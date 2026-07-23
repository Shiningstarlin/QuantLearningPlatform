from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    base_currency: Mapped[str] = mapped_column(String(16), default="HKD")
    initial_equity_hkd: Mapped[float] = mapped_column(Float, default=1_000_000)
    cash_hkd: Mapped[float] = mapped_column(Float, default=1_000_000)
    cash_usd: Mapped[float] = mapped_column(Float, default=0)
    market_value_hkd: Mapped[float] = mapped_column(Float, default=0)
    equity_hkd: Mapped[float] = mapped_column(Float, default=1_000_000)
    fx_usd_hkd: Mapped[float] = mapped_column(Float, default=7.8)
    max_processes: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    tasks = relationship("SimulationTask", back_populates="paper_account", cascade="all, delete-orphan")


class SimulationTask(Base):
    __tablename__ = "simulation_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    paper_account_id: Mapped[int | None] = mapped_column(ForeignKey("paper_accounts.id"), nullable=True, index=True)
    market_asset_id: Mapped[int | None] = mapped_column(ForeignKey("market_assets.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    mode: Mapped[str] = mapped_column(String(32), default="quant")
    strategy_key: Mapped[str] = mapped_column(String(80), default="ma_crossover")
    symbol: Mapped[str] = mapped_column(String(64), default="")
    asset_name: Mapped[str] = mapped_column(String(120), default="")
    asset_type: Mapped[str] = mapped_column(String(32), default="stock")
    exchange: Mapped[str] = mapped_column(String(64), default="")
    base_currency: Mapped[str] = mapped_column(String(16), default="USD")
    allocated_cash: Mapped[float] = mapped_column(Float, default=0)
    allocated_cash_hkd: Mapped[float] = mapped_column(Float, default=0)
    manual_target_exposure: Mapped[float] = mapped_column(Float, default=0)
    fee_profile: Mapped[str] = mapped_column(String(32), default="futu")
    settlement_days: Mapped[int] = mapped_column(Integer, default=0)
    buy_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    sell_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    t_plus_one_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.001)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.0003)
    slippage_rate: Mapped[float] = mapped_column(Float, default=0.0005)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")
    paper_account = relationship("PaperAccount", back_populates="tasks")
    account = relationship("SimulatedAccount", back_populates="task", cascade="all, delete-orphan", uselist=False)
    assets = relationship("WatchAsset", back_populates="task", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="task", cascade="all, delete-orphan")
    trade_logs = relationship("TradeLog", back_populates="task", cascade="all, delete-orphan")


class SimulatedAccount(Base):
    __tablename__ = "simulated_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), unique=True, index=True)
    initial_cash: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    frozen_cash: Mapped[float] = mapped_column(Float, default=0)
    market_value: Mapped[float] = mapped_column(Float, default=0)
    equity: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0)
    cash_available_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("SimulationTask", back_populates="account")


class TradeLog(Base):
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    gross_amount: Mapped[float] = mapped_column(Float)
    tax: Mapped[float] = mapped_column(Float, default=0)
    commission: Mapped[float] = mapped_column(Float, default=0)
    slippage: Mapped[float] = mapped_column(Float, default=0)
    net_amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")
    traded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("SimulationTask", back_populates="trade_logs")


class ControlEvent(Base):
    __tablename__ = "control_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), index=True)
    summary_date: Mapped[date] = mapped_column(Date, index=True)
    cash: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float)
    equity: Mapped[float] = mapped_column(Float)
    daily_return: Mapped[float] = mapped_column(Float, default=0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)


class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("simulation_tasks.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    start_equity: Mapped[float] = mapped_column(Float)
    end_equity: Mapped[float] = mapped_column(Float)
    monthly_return: Mapped[float] = mapped_column(Float, default=0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
