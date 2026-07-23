from app.core.config import settings
from app.market_data.base import MarketDataProvider
from app.market_data.futu import FutuMarketDataProvider
from app.market_data.mock import MockMarketDataProvider
from app.market_data.yahoo import YahooMarketDataProvider


def get_market_data_provider(provider_name: str | None = None) -> MarketDataProvider:
    provider = provider_name or settings.market_data_provider
    if provider == "mock":
        return MockMarketDataProvider()
    if provider == "yahoo":
        return YahooMarketDataProvider()
    if provider == "futu":
        return FutuMarketDataProvider()
    raise NotImplementedError(f"Market data provider is not implemented: {provider}")
