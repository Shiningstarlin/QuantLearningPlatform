from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MarketStatus:
    market: str
    is_open: bool
    timezone: str
    local_time: datetime
    reason: str


class MarketHoursService:
    MARKET_TIMEZONES = {
        "HK": "Asia/Hong_Kong",
        "US": "America/New_York",
    }

    MARKET_SESSIONS = {
        "HK": ((time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))),
        "US": ((time(9, 30), time(16, 0)),),
    }

    @classmethod
    def status_for_exchange(cls, exchange: str, now: datetime | None = None) -> MarketStatus:
        market = cls._normalize_exchange(exchange)
        timezone_name = cls.MARKET_TIMEZONES.get(market, "UTC")
        timezone = ZoneInfo(timezone_name)
        local_time = (now or datetime.now(tz=timezone)).astimezone(timezone)

        if market not in cls.MARKET_SESSIONS:
            return MarketStatus(market=market, is_open=True, timezone=timezone_name, local_time=local_time, reason="unknown")

        if local_time.weekday() >= 5:
            return MarketStatus(market=market, is_open=False, timezone=timezone_name, local_time=local_time, reason="weekend")

        current_time = local_time.time()
        is_open = any(start <= current_time < end for start, end in cls.MARKET_SESSIONS[market])
        return MarketStatus(
            market=market,
            is_open=is_open,
            timezone=timezone_name,
            local_time=local_time,
            reason="regular_session" if is_open else "outside_regular_session",
        )

    @classmethod
    def is_open(cls, exchange: str, now: datetime | None = None) -> bool:
        return cls.status_for_exchange(exchange, now=now).is_open

    @staticmethod
    def _normalize_exchange(exchange: str) -> str:
        value = (exchange or "").upper()
        if value.startswith("HK"):
            return "HK"
        if value.startswith("US") or value in {"NYSE", "NASDAQ", "NYSEARCA"}:
            return "US"
        return value or "UNKNOWN"
