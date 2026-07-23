from datetime import date, datetime

from pydantic import BaseModel, Field


class BacktestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    market_asset_id: int | None = Field(default=None, gt=0)
    yfinance_symbol: str | None = Field(default=None, min_length=1, max_length=64)
    strategy_key: str = "ma_crossover"
    start_date: date
    end_date: date
    initial_cash: float = Field(gt=0)
    tax_rate: float | None = None
    commission_rate: float | None = None
    slippage_rate: float | None = None
    t_plus_one_enabled: bool | None = None


class BacktestBatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    market_asset_id: int | None = Field(default=None, gt=0)
    yfinance_symbol: str | None = Field(default=None, min_length=1, max_length=64)
    strategy_keys: list[str] = Field(min_length=1)
    start_date: date
    end_date: date
    initial_cash: float = Field(gt=0)
    tax_rate: float | None = None
    commission_rate: float | None = None
    slippage_rate: float | None = None
    t_plus_one_enabled: bool | None = None


class BacktestAssetRead(BaseModel):
    key: str
    name: str
    symbol: str
    yfinance_symbol: str
    asset_type: str
    exchange: str
    provider: str = "yfinance"
    currency: str = "USD"
    market_asset_id: int | None = None


class BacktestRunRead(BaseModel):
    id: int
    backtest_task_id: int | None = None
    name: str
    symbol: str
    asset_name: str
    asset_type: str
    exchange: str
    provider: str
    strategy_key: str
    status: str
    start_date: date
    end_date: date
    initial_cash: float
    final_cash: float
    final_market_value: float
    final_equity: float
    total_return: float
    max_drawdown: float
    trade_count: int
    win_rate: float
    tax_rate: float
    commission_rate: float
    slippage_rate: float
    t_plus_one_enabled: bool
    error_message: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class BacktestTaskRead(BaseModel):
    id: int
    name: str
    symbol: str
    asset_name: str
    asset_type: str
    exchange: str
    provider: str
    currency: str
    status: str
    start_date: date
    end_date: date
    initial_cash: float
    strategy_count: int
    best_run_id: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    runs: list[BacktestRunRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BacktestTradeRead(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    gross_amount: float
    tax: float
    commission: float
    slippage: float
    net_amount: float
    realized_pnl: float
    reason: str
    traded_on: date

    model_config = {"from_attributes": True}


class BacktestEquityPointRead(BaseModel):
    id: int
    point_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    cash: float
    market_value: float
    equity: float
    position_quantity: float

    model_config = {"from_attributes": True}


class BacktestAssetMetricsRead(BaseModel):
    start_price: float
    end_price: float
    raw_return: float
    annualized_volatility: float
    max_drawdown: float
    high_price: float
    low_price: float


class BacktestPreviewPointRead(BaseModel):
    point_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float


class BacktestPreviewRead(BaseModel):
    symbol: str
    name: str
    currency: str
    points: list[BacktestPreviewPointRead]
    asset_metrics: BacktestAssetMetricsRead | None = None


class BacktestDetailRead(BaseModel):
    task: BacktestTaskRead | None = None
    run: BacktestRunRead
    sibling_runs: list[BacktestRunRead] = Field(default_factory=list)
    equity_points: list[BacktestEquityPointRead]
    trades: list[BacktestTradeRead]
    asset_metrics: BacktestAssetMetricsRead | None = None


class BacktestBatchRead(BaseModel):
    task: BacktestTaskRead | None = None
    runs: list[BacktestRunRead]


class BacktestComparisonRead(BaseModel):
    runs: list[BacktestRunRead]
