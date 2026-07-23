from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.market_data.base import MarketDataProvider
from app.models.position import Position
from app.models.simulation import SimulationTask, TradeLog
from app.schemas.trading import OrderIntent
from app.services.fees import FutuFeeService


class SimulationEngine:
    def __init__(self, db: Session, market_data: MarketDataProvider):
        self.db = db
        self.market_data = market_data

    def execute_intent(self, task: SimulationTask, intent: OrderIntent) -> TradeLog:
        if task.status != "running":
            raise HTTPException(status_code=400, detail="Task is not running")
        self._release_settled_cash(task)
        if intent.side == "buy" and task.buy_frozen:
            raise HTTPException(status_code=400, detail="Buying is frozen")
        if intent.side == "sell" and task.sell_frozen:
            raise HTTPException(status_code=400, detail="Selling is frozen")
        if intent.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")

        quote = self.market_data.get_quote(intent.symbol)
        execution_price = self._apply_slippage(price=quote.price, side=intent.side, rate=task.slippage_rate)
        gross_amount = execution_price * intent.quantity
        fee_breakdown = FutuFeeService.calculate(task.exchange, intent.side, gross_amount, intent.quantity)
        commission = fee_breakdown.commission + fee_breakdown.platform_fee + fee_breakdown.settlement_fee + fee_breakdown.regulatory_fee
        tax = fee_breakdown.tax
        slippage = abs(execution_price - quote.price) * intent.quantity

        if intent.side == "buy":
            net_amount = gross_amount + commission + slippage
            self._buy(task, intent.symbol, intent.quantity, execution_price, net_amount)
        elif intent.side == "sell":
            net_amount = gross_amount - commission - tax - slippage
            self._sell(task, intent.symbol, intent.quantity, execution_price, net_amount)
        else:
            raise HTTPException(status_code=400, detail="Unsupported side")

        log = TradeLog(
            task_id=task.id,
            symbol=intent.symbol.upper(),
            side=intent.side,
            quantity=intent.quantity,
            price=execution_price,
            gross_amount=gross_amount,
            tax=tax,
            commission=commission,
            slippage=slippage,
            net_amount=net_amount,
            reason=intent.reason,
        )
        self.db.add(log)
        self._refresh_account(task)
        self.db.commit()
        self.db.refresh(log)
        return log

    def _buy(self, task: SimulationTask, symbol: str, quantity: float, price: float, net_amount: float) -> None:
        if task.account.cash < net_amount:
            raise HTTPException(status_code=400, detail="Insufficient cash")

        position = self._get_or_create_position(task.id, symbol)
        self._release_settled_quantity(task, position)
        total_cost = position.average_cost * position.quantity + price * quantity
        position.quantity += quantity
        if task.settlement_days > 0:
            position.available_on = date.today() + timedelta(days=task.settlement_days)
        else:
            position.available_quantity += quantity
            position.available_on = date.today()
        position.average_cost = total_cost / position.quantity
        position.last_price = price
        position.market_value = position.quantity * price
        position.opened_on = position.opened_on or date.today()
        position.updated_at = datetime.now(timezone.utc)
        task.account.cash -= net_amount

    def _sell(self, task: SimulationTask, symbol: str, quantity: float, price: float, net_amount: float) -> None:
        position = self._get_position(task.id, symbol)
        if position is None or position.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient position")
        self._release_settled_quantity(task, position)
        if task.settlement_days > 0 and position.available_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Quantity is locked by T+{task.settlement_days} settlement")

        realized_pnl = (price - position.average_cost) * quantity
        position.quantity -= quantity
        position.available_quantity -= quantity
        position.last_price = price
        position.market_value = position.quantity * price
        position.updated_at = datetime.now(timezone.utc)
        if task.settlement_days > 0:
            task.account.frozen_cash += net_amount
            task.account.cash_available_on = date.today() + timedelta(days=task.settlement_days)
        else:
            task.account.cash += net_amount
        task.account.realized_pnl += realized_pnl

    @staticmethod
    def _release_settled_quantity(task: SimulationTask, position: Position) -> None:
        if task.settlement_days <= 0:
            position.available_quantity = position.quantity
            return
        if position.available_on is not None and position.available_on <= date.today():
            position.available_quantity = position.quantity

    @staticmethod
    def _release_settled_cash(task: SimulationTask) -> None:
        if task.account is None:
            return
        if task.account.cash_available_on is not None and task.account.cash_available_on <= date.today():
            task.account.cash += task.account.frozen_cash
            task.account.frozen_cash = 0
            task.account.cash_available_on = None

    def _refresh_account(self, task: SimulationTask) -> None:
        positions = self.db.scalars(select(Position).where(Position.task_id == task.id))
        task.account.market_value = sum(position.market_value for position in positions)
        task.account.equity = task.account.cash + task.account.frozen_cash + task.account.market_value
        task.account.updated_at = datetime.now(timezone.utc)

    def _get_or_create_position(self, task_id: int, symbol: str) -> Position:
        position = self._get_position(task_id, symbol)
        if position is None:
            position = Position(task_id=task_id, symbol=symbol.upper())
            self.db.add(position)
            self.db.flush()
        return position

    def _get_position(self, task_id: int, symbol: str) -> Position | None:
        return self.db.scalar(select(Position).where(Position.task_id == task_id, Position.symbol == symbol.upper()))

    @staticmethod
    def _apply_slippage(price: float, side: str, rate: float) -> float:
        multiplier = 1 + rate if side == "buy" else 1 - rate
        return round(price * multiplier, 6)
