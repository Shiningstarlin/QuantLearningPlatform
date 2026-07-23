import threading
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.market_data.base import MarketDataProvider, Quote


class FutuMarketDataProvider(MarketDataProvider):
    _rate_limit_lock = threading.Lock()
    _snapshot_request_times: list[float] = []

    def get_quote(self, symbol: str) -> Quote:
        quotes = self.get_quotes([symbol])
        if not quotes:
            raise RuntimeError(f"Futu did not return a quote for {symbol}")
        return quotes[0]

    def get_quotes(self, symbols: list[str]) -> list[Quote]:
        normalized_symbols = [self._normalize_symbol(symbol) for symbol in symbols if symbol.strip()]
        if not normalized_symbols:
            return []

        self._check_rate_limit()

        try:
            from futu import OpenQuoteContext, RET_OK
        except ImportError as exc:
            raise RuntimeError("Install futu-api first: pip install futu-api") from exc

        quote_ctx = OpenQuoteContext(host=settings.futu_host, port=settings.futu_port)
        try:
            ret, data = quote_ctx.get_market_snapshot(normalized_symbols)
            if ret != RET_OK:
                raise RuntimeError(f"Futu snapshot request failed: {data}")

            quotes: list[Quote] = []
            for _, row in data.iterrows():
                code = str(row.get("code") or "").upper()
                price = row.get("last_price")
                if not code or price is None or float(price) <= 0:
                    continue
                quotes.append(
                    Quote(
                        symbol=code,
                        price=float(price),
                        currency=self._currency_for_symbol(code),
                        timestamp=self._timestamp(row.get("update_time"), code),
                        provider="futu",
                    )
                )
            return quotes
        finally:
            quote_ctx.close()

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        symbol = symbol.strip().upper()
        if "." in symbol:
            return symbol
        if symbol.isdigit():
            return f"HK.{symbol.zfill(5)}"
        if symbol.isalpha():
            return f"US.{symbol}"
        return symbol

    @staticmethod
    def _currency_for_symbol(symbol: str) -> str:
        if symbol.startswith("HK."):
            return "HKD"
        if symbol.startswith("US."):
            return "USD"
        if symbol.startswith(("SH.", "SZ.")):
            return "CNY"
        return ""

    @staticmethod
    def _timestamp(value, symbol: str) -> datetime:
        if value:
            try:
                parsed = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
                return parsed.replace(tzinfo=FutuMarketDataProvider._timezone_for_symbol(symbol)).astimezone(timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def _timezone_for_symbol(symbol: str):
        if symbol.startswith("US."):
            return ZoneInfo("America/New_York")
        if symbol.startswith(("SH.", "SZ.")):
            return ZoneInfo("Asia/Shanghai")
        if symbol.startswith("HK."):
            return ZoneInfo("Asia/Hong_Kong")
        return timezone(timedelta(hours=8))

    @classmethod
    def _check_rate_limit(cls) -> None:
        now = time.monotonic()
        with cls._rate_limit_lock:
            cls._snapshot_request_times = [
                request_time for request_time in cls._snapshot_request_times if now - request_time < 60
            ]
            if len(cls._snapshot_request_times) >= settings.futu_snapshot_max_requests_per_minute:
                raise RuntimeError("Futu snapshot rate limit reached; please retry later")
            cls._snapshot_request_times.append(now)
