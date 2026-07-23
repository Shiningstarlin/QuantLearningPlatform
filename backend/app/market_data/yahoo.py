from datetime import datetime, timezone
from io import StringIO
import csv

from app.market_data.base import MarketDataProvider, Quote
from app.market_data.mock import MockMarketDataProvider


class YahooMarketDataProvider(MarketDataProvider):
    def get_quote(self, symbol: str) -> Quote:
        try:
            return self._get_yahoo_quote(symbol)
        except Exception:
            fallback = MockMarketDataProvider().get_quote(symbol)
            return Quote(
                symbol=fallback.symbol,
                price=fallback.price,
                currency=fallback.currency,
                timestamp=fallback.timestamp,
                provider="mock-fallback",
            )

    def _get_yahoo_quote(self, symbol: str) -> Quote:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("Install backend dependencies first: pip install -e .") from exc

        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("last_price") or info.get("regular_market_price")
        currency = info.get("currency") or "USD"

        if price is None:
            history = ticker.history(period="1d", interval="1m")
            if history.empty:
                raise RuntimeError(f"Yahoo Finance did not return a quote for {symbol}")
            price = float(history["Close"].dropna().iloc[-1])

        return Quote(
            symbol=symbol.upper(),
            price=float(price),
            currency=str(currency),
            timestamp=datetime.now(timezone.utc),
            provider="yahoo",
        )

    def _get_stooq_quote(self, symbol: str) -> Quote:
        import requests

        stooq_symbol = symbol.lower()
        if "." not in stooq_symbol:
            stooq_symbol = f"{stooq_symbol}.us"

        response = requests.get(
            "https://stooq.com/q/l/",
            params={"s": stooq_symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"},
            timeout=10,
        )
        response.raise_for_status()
        rows = list(csv.DictReader(StringIO(response.text)))
        if not rows or rows[0].get("Close") in (None, "N/D"):
            raise RuntimeError(f"Stooq did not return a quote for {symbol}")

        return Quote(
            symbol=symbol.upper(),
            price=float(rows[0]["Close"]),
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            provider="stooq",
        )
