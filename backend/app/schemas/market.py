from datetime import datetime

from pydantic import BaseModel, Field


class MarketAssetCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = ""
    asset_type: str = "stock"
    exchange: str = ""
    provider: str = "futu"


class MarketAssetRead(BaseModel):
    id: int
    symbol: str
    name: str
    asset_type: str
    exchange: str
    provider: str
    currency: str
    settlement_days: int
    enabled: bool

    model_config = {"from_attributes": True}


class MarketQuoteRead(BaseModel):
    symbol: str
    provider: str
    price: float
    currency: str
    quote_time: datetime

    model_config = {"from_attributes": True}


class MarketStatusRead(BaseModel):
    market: str
    is_open: bool
    timezone: str
    local_time: datetime
    reason: str

    model_config = {"from_attributes": True}


class MarketBoardRow(BaseModel):
    asset: MarketAssetRead
    latest_quote: MarketQuoteRead | None = None
    history: list[MarketQuoteRead] = []
    market_status: MarketStatusRead | None = None
