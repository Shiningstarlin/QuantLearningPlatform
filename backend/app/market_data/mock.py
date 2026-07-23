from datetime import datetime, timezone

from app.market_data.base import MarketDataProvider, Quote


class MockMarketDataProvider(MarketDataProvider):
    def get_quote(self, symbol: str) -> Quote:
        seed = sum(ord(char) for char in symbol.upper())
        price = 50 + (seed % 200) + ((seed % 17) / 10)
        return Quote(
            symbol=symbol.upper(),
            price=round(price, 2),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            provider="mock",
        )
