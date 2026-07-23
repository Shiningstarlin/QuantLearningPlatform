from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MarketAsset(Base):
    __tablename__ = "market_assets"
    __table_args__ = (UniqueConstraint("symbol", "provider", name="uq_market_asset_symbol_provider"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    asset_type: Mapped[str] = mapped_column(String(32), default="stock")
    exchange: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(32), default="yahoo")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    quotes = relationship("MarketQuote", back_populates="asset", cascade="all, delete-orphan")

    @property
    def currency(self) -> str:
        if self.exchange.upper() == "HK":
            return "HKD"
        return "USD"

    @property
    def settlement_days(self) -> int:
        if self.exchange.upper() == "HK":
            return 2
        if self.exchange.upper() == "US":
            return 1
        return 0


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("market_assets.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    quote_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    asset = relationship("MarketAsset", back_populates="quotes")
