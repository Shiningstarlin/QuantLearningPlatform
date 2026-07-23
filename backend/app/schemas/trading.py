from datetime import datetime

from pydantic import BaseModel


class OrderIntent(BaseModel):
    symbol: str
    side: str
    quantity: float
    reason: str = ""


class TradeLogRead(BaseModel):
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
    reason: str
    traded_at: datetime

    model_config = {"from_attributes": True}
