from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.asset import WatchAsset
from app.models.market import MarketAsset
from app.market_data.factory import get_market_data_provider
from app.models.position import Position
from app.models.market import MarketQuote
from app.models.simulation import (
    AccountDailySummary,
    AccountMonthlySummary,
    ControlEvent,
    PaperAccount,
    SimulatedAccount,
    SimulationTask,
    TradeLog,
)
from app.schemas.simulation import (
    AccountOverallPerformanceRead,
    AccountDailySummaryRead,
    AccountMonthlySummaryRead,
    ControlRequest,
    InvestmentProcessCreate,
    ManualExposureUpdate,
    PaperAccountCreate,
    PaperAccountPerformanceRead,
    SimulationTaskCreate,
)
from app.schemas.trading import OrderIntent
from app.services.fx import FxService
from app.simulation.engine import SimulationEngine


class SimulationTaskService:
    MAX_ACCOUNTS_PER_USER = 3
    DEFAULT_INITIAL_HKD = 1_000_000
    SETTLEMENT_ZONE = ZoneInfo("Asia/Shanghai")
    SETTLEMENT_HOUR = 6

    def __init__(self, db: Session):
        self.db = db
        self.fx = FxService()

    def list_accounts(self, user_id: int) -> list[PaperAccount]:
        accounts = list(
            self.db.scalars(
                select(PaperAccount)
                .where(PaperAccount.user_id == user_id)
                .options(selectinload(PaperAccount.tasks).selectinload(SimulationTask.account))
                .order_by(PaperAccount.created_at.desc())
            )
        )
        for account in accounts:
            self.refresh_paper_account(account)
        self.db.commit()
        return accounts

    def get_account_performance(self, user_id: int, account_id: int, limit: int = 90) -> PaperAccountPerformanceRead:
        account = self._load_account(user_id, account_id)
        self.capture_account_snapshot(account)
        daily = list(
            self.db.scalars(
                select(AccountDailySummary)
                .where(AccountDailySummary.paper_account_id == account.id)
                .order_by(AccountDailySummary.summary_date.desc())
                .limit(max(1, min(limit, 365)))
            )
        )[::-1]
        monthly = list(
            self.db.scalars(
                select(AccountMonthlySummary)
                .where(AccountMonthlySummary.paper_account_id == account.id)
                .order_by(AccountMonthlySummary.year.desc(), AccountMonthlySummary.month.desc())
                .limit(24)
            )
        )[::-1]
        latest_equity = account.equity_hkd
        equity_series = [account.initial_equity_hkd, *(row.equity_hkd for row in daily), latest_equity]
        peak_equity = max(equity_series) if equity_series else latest_equity
        max_drawdown = self._max_drawdown(equity_series)
        trade_count = self._trade_count(account.id)
        total_pnl = latest_equity - account.initial_equity_hkd
        self.db.commit()
        return PaperAccountPerformanceRead(
            settlement_timezone="Asia/Shanghai",
            settlement_time="06:00",
            as_of=datetime.now(timezone.utc),
            overall=AccountOverallPerformanceRead(
                initial_equity_hkd=account.initial_equity_hkd,
                current_equity_hkd=latest_equity,
                total_pnl_hkd=total_pnl,
                total_return=total_pnl / account.initial_equity_hkd if account.initial_equity_hkd else 0,
                peak_equity_hkd=peak_equity,
                max_drawdown=max_drawdown,
                total_trade_count=trade_count,
            ),
            daily=[AccountDailySummaryRead.model_validate(row) for row in daily],
            monthly=[AccountMonthlySummaryRead.model_validate(row) for row in monthly],
        )

    def capture_all_accounts(self) -> None:
        accounts = list(
            self.db.scalars(
                select(PaperAccount).options(
                    selectinload(PaperAccount.tasks).selectinload(SimulationTask.account),
                    selectinload(PaperAccount.tasks).selectinload(SimulationTask.positions),
                )
            )
        )
        for account in accounts:
            self.capture_account_snapshot(account)
        self.db.commit()

    def capture_account_snapshot(self, account: PaperAccount) -> AccountDailySummary:
        self._mark_to_market(account)
        settlement_date = self._settlement_date()
        previous = self.db.scalar(
            select(AccountDailySummary)
            .where(
                AccountDailySummary.paper_account_id == account.id,
                AccountDailySummary.summary_date < settlement_date,
            )
            .order_by(AccountDailySummary.summary_date.desc())
            .limit(1)
        )
        previous_equity = previous.equity_hkd if previous is not None else account.initial_equity_hkd
        summary = self.db.scalar(
            select(AccountDailySummary).where(
                AccountDailySummary.paper_account_id == account.id,
                AccountDailySummary.summary_date == settlement_date,
            )
        )
        if summary is None:
            summary = AccountDailySummary(paper_account_id=account.id, summary_date=settlement_date)
            self.db.add(summary)

        trade_count = self._trade_count(account.id, self._settlement_start_utc(settlement_date))
        summary.snapshot_at = datetime.now(timezone.utc)
        summary.cash_hkd = account.cash_hkd
        summary.market_value_hkd = account.market_value_hkd
        summary.equity_hkd = account.equity_hkd
        summary.net_cash_flow_hkd = 0
        summary.pnl_hkd = account.equity_hkd - previous_equity
        summary.return_rate = summary.pnl_hkd / previous_equity if previous_equity else 0
        summary.cumulative_pnl_hkd = account.equity_hkd - account.initial_equity_hkd
        summary.trade_count = trade_count
        self.db.flush()
        self._upsert_monthly_summary(account, settlement_date)
        self.db.flush()
        return summary

    def _upsert_monthly_summary(self, account: PaperAccount, settlement_date: date) -> None:
        monthly = self.db.scalar(
            select(AccountMonthlySummary).where(
                AccountMonthlySummary.paper_account_id == account.id,
                AccountMonthlySummary.year == settlement_date.year,
                AccountMonthlySummary.month == settlement_date.month,
            )
        )
        if monthly is None:
            monthly = AccountMonthlySummary(
                paper_account_id=account.id,
                year=settlement_date.year,
                month=settlement_date.month,
            )
            self.db.add(monthly)

        month_start = date(settlement_date.year, settlement_date.month, 1)
        prior = self.db.scalar(
            select(AccountDailySummary)
            .where(
                AccountDailySummary.paper_account_id == account.id,
                AccountDailySummary.summary_date < month_start,
            )
            .order_by(AccountDailySummary.summary_date.desc())
            .limit(1)
        )
        month_rows = list(
            self.db.scalars(
                select(AccountDailySummary)
                .where(
                    AccountDailySummary.paper_account_id == account.id,
                    AccountDailySummary.summary_date >= month_start,
                    AccountDailySummary.summary_date <= settlement_date,
                )
                .order_by(AccountDailySummary.summary_date.asc())
            )
        )
        start_equity = prior.equity_hkd if prior is not None else account.initial_equity_hkd
        equities = [start_equity, *(row.equity_hkd for row in month_rows)]
        end_equity = equities[-1] if equities else account.equity_hkd
        pnl = end_equity - start_equity
        monthly.start_equity_hkd = start_equity
        monthly.end_equity_hkd = end_equity
        monthly.net_cash_flow_hkd = 0
        monthly.pnl_hkd = pnl
        monthly.return_rate = pnl / start_equity if start_equity else 0
        monthly.max_drawdown = self._max_drawdown(equities)
        monthly.trade_count = sum(row.trade_count for row in month_rows)
        monthly.updated_at = datetime.now(timezone.utc)

    def _mark_to_market(self, account: PaperAccount) -> None:
        task_ids = [task.id for task in account.tasks if task.account is not None and task.status != "ended"]
        asset_ids = [task.market_asset_id for task in account.tasks if task.market_asset_id is not None and task.id in task_ids]
        latest_by_asset: dict[int, MarketQuote] = {}
        if asset_ids:
            ranked = (
                select(
                    MarketQuote.id.label("quote_id"),
                    func.row_number()
                    .over(partition_by=MarketQuote.asset_id, order_by=[MarketQuote.quote_time.desc(), MarketQuote.id.desc()])
                    .label("rank"),
                )
                .where(MarketQuote.asset_id.in_(asset_ids))
                .subquery()
            )
            quotes = self.db.scalars(
                select(MarketQuote).join(ranked, MarketQuote.id == ranked.c.quote_id).where(ranked.c.rank == 1)
            )
            latest_by_asset = {quote.asset_id: quote for quote in quotes}

        for task in account.tasks:
            if task.account is None or task.status == "ended":
                continue
            quote = latest_by_asset.get(task.market_asset_id)
            if quote is not None:
                for position in task.positions:
                    if position.quantity > 0:
                        position.last_price = quote.price
                        position.market_value = position.quantity * quote.price
            task.account.market_value = sum(position.market_value for position in task.positions)
            task.account.equity = task.account.cash + task.account.frozen_cash + task.account.market_value
            task.account.updated_at = datetime.now(timezone.utc)
        self.refresh_paper_account(account)

    def _trade_count(self, account_id: int, since: datetime | None = None) -> int:
        statement = (
            select(func.count(TradeLog.id))
            .join(SimulationTask, SimulationTask.id == TradeLog.task_id)
            .where(SimulationTask.paper_account_id == account_id)
        )
        if since is not None:
            statement = statement.where(TradeLog.traded_at >= since)
        return int(self.db.scalar(statement) or 0)

    @classmethod
    def _settlement_date(cls, now: datetime | None = None) -> date:
        local_now = (now or datetime.now(timezone.utc)).astimezone(cls.SETTLEMENT_ZONE)
        return local_now.date() if local_now.hour >= cls.SETTLEMENT_HOUR else local_now.date() - timedelta(days=1)

    @classmethod
    def _settlement_start_utc(cls, settlement_date: date) -> datetime:
        local_start = datetime.combine(settlement_date, time(cls.SETTLEMENT_HOUR), tzinfo=cls.SETTLEMENT_ZONE)
        return local_start.astimezone(timezone.utc)

    @staticmethod
    def _max_drawdown(equities: list[float]) -> float:
        peak = 0.0
        max_drawdown = 0.0
        for equity in equities:
            peak = max(peak, equity)
            if peak:
                max_drawdown = min(max_drawdown, (equity - peak) / peak)
        return max_drawdown

    def create_account(self, user_id: int, payload: PaperAccountCreate) -> PaperAccount:
        account_count = self.db.scalar(select(func.count()).select_from(PaperAccount).where(PaperAccount.user_id == user_id))
        if account_count is None:
            account_count = 0
        if account_count >= self.MAX_ACCOUNTS_PER_USER:
            raise HTTPException(status_code=400, detail="每个用户当前最多可以创建 3 个模拟账户")

        fx_rate = self.fx.usd_hkd()
        account = PaperAccount(
            user_id=user_id,
            name=payload.name,
            initial_equity_hkd=self.DEFAULT_INITIAL_HKD,
            cash_hkd=self.DEFAULT_INITIAL_HKD,
            equity_hkd=self.DEFAULT_INITIAL_HKD,
            fx_usd_hkd=fx_rate,
        )
        self.db.add(account)
        self.db.commit()
        return self._load_account(user_id, account.id)

    def create_task(self, user_id: int, payload: SimulationTaskCreate) -> SimulationTask:
        account = self._default_or_create_account(user_id)
        process_payload = InvestmentProcessCreate(
            name=payload.name,
            market_asset_id=payload.market_asset_id,
            allocated_cash=payload.initial_cash if payload.initial_cash is not None else 100_000,
            allocated_currency=None,
            mode="quant",
            strategy_key=payload.strategy_key,
            manual_target_exposure=0,
            t_plus_one_enabled=None,
        )
        return self.create_process(user_id, account.id, process_payload)

    def create_process(self, user_id: int, account_id: int, payload: InvestmentProcessCreate) -> SimulationTask:
        account = self._load_account(user_id, account_id)
        active_count = len([task for task in account.tasks if task.status != "ended"])
        if active_count >= account.max_processes:
            raise HTTPException(status_code=400, detail="同一模拟账户最多允许 20 个投资进程")

        market_asset = self.db.get(MarketAsset, payload.market_asset_id)
        if market_asset is None or not market_asset.enabled:
            raise HTTPException(status_code=400, detail="Please choose an enabled market board asset")

        currency = self._currency_for_asset(market_asset)
        settlement_days = self._settlement_days_for_asset(market_asset)
        allocated_hkd = self.fx.to_hkd(payload.allocated_cash, currency)
        if account.cash_hkd < allocated_hkd:
            raise HTTPException(status_code=400, detail="账户可用余额不足，无法分配这笔资金")

        task = SimulationTask(
            user_id=user_id,
            paper_account_id=account.id,
            market_asset_id=market_asset.id,
            name=payload.name,
            status="running",
            mode=payload.mode,
            strategy_key=payload.strategy_key,
            symbol=market_asset.symbol,
            asset_name=market_asset.name,
            asset_type=market_asset.asset_type,
            exchange=market_asset.exchange,
            base_currency=currency,
            allocated_cash=payload.allocated_cash,
            allocated_cash_hkd=allocated_hkd,
            manual_target_exposure=payload.manual_target_exposure,
            tax_rate=0,
            commission_rate=0,
            slippage_rate=settings.default_slippage_rate,
            settlement_days=settlement_days,
            t_plus_one_enabled=settlement_days > 0,
        )
        task.account = SimulatedAccount(
            initial_cash=payload.allocated_cash,
            cash=payload.allocated_cash,
            equity=payload.allocated_cash,
        )
        self.db.add(task)
        self.db.flush()
        account.cash_hkd -= allocated_hkd
        self.db.add(
            WatchAsset(
                task_id=task.id,
                symbol=market_asset.symbol,
                name=market_asset.name,
                asset_type=market_asset.asset_type,
                exchange=market_asset.exchange,
            )
        )
        self.db.commit()

        if payload.mode == "manual" and payload.manual_target_exposure > 0:
            self.update_manual_exposure(user_id, task.id, ManualExposureUpdate(target_exposure=payload.manual_target_exposure))

        self.refresh_paper_account(account)
        self.db.commit()
        return self._load_task(user_id, task.id)

    def update_manual_exposure(self, user_id: int, task_id: int, payload: ManualExposureUpdate) -> SimulationTask:
        task = self._load_task(user_id, task_id)
        if task.mode != "manual":
            raise HTTPException(status_code=400, detail="只有手动进程可以修改目标投入比例")
        if task.status != "running":
            raise HTTPException(status_code=400, detail="进程未运行，无法调整")

        market_data = get_market_data_provider()
        quote = market_data.get_quote(task.symbol)
        position = self.db.scalar(select(Position).where(Position.task_id == task.id, Position.symbol == task.symbol.upper()))
        current_quantity = position.quantity if position else 0
        current_market_value = current_quantity * quote.price
        target_market_value = task.account.equity * payload.target_exposure
        delta_value = target_market_value - current_market_value
        min_trade_value = max(quote.price * 0.0001, 1)

        if abs(delta_value) > min_trade_value:
            quantity = abs(delta_value) / quote.price
            side = "buy" if delta_value > 0 else "sell"
            SimulationEngine(self.db, market_data).execute_intent(
                task,
                OrderIntent(symbol=task.symbol, side=side, quantity=quantity, reason="manual target exposure adjustment"),
            )
        task.manual_target_exposure = payload.target_exposure
        if task.paper_account:
            self.refresh_paper_account(task.paper_account)
        self.db.commit()
        return self._load_task(user_id, task_id)

    def apply_control(self, user_id: int, task_id: int, payload: ControlRequest) -> SimulationTask:
        task = self._load_task(user_id, task_id)
        event_type = payload.event_type

        if event_type == "freeze_buy":
            task.buy_frozen = True
        elif event_type == "resume_buy":
            task.buy_frozen = False
        elif event_type == "freeze_sell":
            task.sell_frozen = True
        elif event_type == "resume_sell":
            task.sell_frozen = False
        elif event_type == "add_cash":
            self._change_cash(task, payload.amount, positive=True)
        elif event_type == "remove_cash":
            self._change_cash(task, payload.amount, positive=False)
        elif event_type == "start":
            task.status = "running"
        elif event_type == "pause":
            task.status = "paused"
        elif event_type == "end":
            if task.paper_account and task.account:
                task.paper_account.cash_hkd += self.fx.to_hkd(task.account.equity, task.base_currency)
            task.status = "ended"
            task.ended_at = datetime.now(timezone.utc)
        else:
            raise HTTPException(status_code=400, detail="Unsupported control event")

        self.db.add(ControlEvent(task_id=task.id, event_type=event_type, amount=payload.amount, note=payload.note))
        if task.paper_account:
            self.refresh_paper_account(task.paper_account)
        self.db.commit()
        return self._load_task(user_id, task_id)

    def _change_cash(self, task: SimulationTask, amount: float | None, positive: bool) -> None:
        if amount is None or amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        if task.account is None:
            raise HTTPException(status_code=400, detail="Task account is missing")

        delta = amount if positive else -amount
        if not positive and task.account.cash < amount:
            raise HTTPException(status_code=400, detail="Insufficient cash")
        if task.paper_account:
            amount_hkd = self.fx.to_hkd(amount, task.base_currency)
            if positive:
                if task.paper_account.cash_hkd < amount_hkd:
                    raise HTTPException(status_code=400, detail="模拟账户未分配资金不足")
                task.paper_account.cash_hkd -= amount_hkd
            else:
                task.paper_account.cash_hkd += amount_hkd
        task.account.cash += delta
        task.account.equity += delta

    def refresh_paper_account(self, account: PaperAccount) -> None:
        market_value_hkd = 0.0
        for task in account.tasks:
            if task.account is None or task.status == "ended":
                continue
            process_equity_hkd = self.fx.to_hkd(task.account.equity, task.base_currency)
            process_cash_hkd = self.fx.to_hkd(task.account.cash + task.account.frozen_cash, task.base_currency)
            market_value_hkd += max(process_equity_hkd - process_cash_hkd, 0)
        account.market_value_hkd = market_value_hkd
        account.equity_hkd = account.cash_hkd + sum(
            self.fx.to_hkd(task.account.equity, task.base_currency)
            for task in account.tasks
            if task.account is not None and task.status != "ended"
        )
        account.cash_usd = self.fx.from_hkd(account.cash_hkd, "USD")
        account.fx_usd_hkd = self.fx.usd_hkd()
        account.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _currency_for_asset(asset: MarketAsset) -> str:
        return asset.currency

    @staticmethod
    def _settlement_days_for_asset(asset: MarketAsset) -> int:
        return asset.settlement_days

    def _default_or_create_account(self, user_id: int) -> PaperAccount:
        account = self.db.scalar(
            select(PaperAccount)
            .where(PaperAccount.user_id == user_id, PaperAccount.status == "active")
            .options(selectinload(PaperAccount.tasks).selectinload(SimulationTask.account))
            .order_by(PaperAccount.created_at)
        )
        if account is not None:
            return account
        return self.create_account(user_id, PaperAccountCreate(name="默认模拟账户"))

    def _load_account(self, user_id: int, account_id: int) -> PaperAccount:
        account = self.db.scalar(
            select(PaperAccount)
            .where(PaperAccount.id == account_id, PaperAccount.user_id == user_id)
            .options(selectinload(PaperAccount.tasks).selectinload(SimulationTask.account))
        )
        if account is None:
            raise HTTPException(status_code=404, detail="模拟账户不存在")
        return account

    def _load_task(self, user_id: int, task_id: int) -> SimulationTask:
        task = self.db.scalar(
            select(SimulationTask)
            .where(SimulationTask.id == task_id, SimulationTask.user_id == user_id)
            .options(selectinload(SimulationTask.account), selectinload(SimulationTask.paper_account))
        )
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
