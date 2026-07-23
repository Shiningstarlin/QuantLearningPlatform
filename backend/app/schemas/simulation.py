from datetime import date, datetime

from pydantic import BaseModel, Field


class SimulationTaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    initial_cash: float | None = Field(default=None, gt=0)
    market_asset_id: int = Field(gt=0)
    strategy_key: str = "ma_crossover"
    base_currency: str = "HKD"
    tax_rate: float | None = None
    commission_rate: float | None = None
    slippage_rate: float | None = None
    t_plus_one_enabled: bool | None = None


class PaperAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class InvestmentProcessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    market_asset_id: int = Field(gt=0)
    allocated_cash: float = Field(gt=0)
    allocated_currency: str | None = None
    mode: str = "manual"
    strategy_key: str = "ma_crossover"
    manual_target_exposure: float = Field(default=0, ge=0, le=1)
    t_plus_one_enabled: bool | None = None


class ManualExposureUpdate(BaseModel):
    target_exposure: float = Field(ge=0, le=1)


class SimulatedAccountRead(BaseModel):
    initial_cash: float
    cash: float
    frozen_cash: float
    market_value: float
    equity: float
    realized_pnl: float
    cash_available_on: date | None = None

    model_config = {"from_attributes": True}


class SimulationTaskRead(BaseModel):
    id: int
    paper_account_id: int | None = None
    market_asset_id: int | None = None
    name: str
    status: str
    mode: str
    strategy_key: str
    symbol: str
    asset_name: str
    asset_type: str
    exchange: str
    base_currency: str
    allocated_cash: float
    allocated_cash_hkd: float
    manual_target_exposure: float
    fee_profile: str
    settlement_days: int
    buy_frozen: bool
    sell_frozen: bool
    t_plus_one_enabled: bool
    tax_rate: float
    commission_rate: float
    slippage_rate: float
    created_at: datetime
    account: SimulatedAccountRead | None = None

    model_config = {"from_attributes": True}


class PaperAccountRead(BaseModel):
    id: int
    name: str
    base_currency: str
    initial_equity_hkd: float
    cash_hkd: float
    cash_usd: float
    market_value_hkd: float
    equity_hkd: float
    fx_usd_hkd: float
    max_processes: int
    status: str
    created_at: datetime
    updated_at: datetime
    tasks: list[SimulationTaskRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class FeeLineRead(BaseModel):
    name: str
    value: str


class FeeScheduleRead(BaseModel):
    market: str
    title: str
    lines: list[FeeLineRead]
    settlement_note: str
    source_url: str


class SimulationFeeSchedulesRead(BaseModel):
    schedules: list[FeeScheduleRead]


class ControlRequest(BaseModel):
    event_type: str
    amount: float | None = None
    note: str = ""
