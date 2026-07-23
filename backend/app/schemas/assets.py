from pydantic import BaseModel, Field


class WatchAssetCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = ""
    asset_type: str = "stock"
    exchange: str = ""


class WatchAssetRead(BaseModel):
    id: int
    symbol: str
    name: str
    asset_type: str
    exchange: str
    enabled: bool

    model_config = {"from_attributes": True}
