from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.market_data.factory import get_market_data_provider
from app.models.market import MarketAsset, MarketQuote
from app.schemas.market import MarketAssetCreate
from app.services.market_hours import MarketHoursService


class MarketBoardService:
    PROVIDER = "futu"

    def __init__(self, db: Session):
        self.db = db

    def ensure_default_assets(self) -> None:
        default_assets = [self._parse_default_asset(raw_symbol) for raw_symbol in settings.market_board_default_symbols.split(",")]
        default_keys = {(symbol, self.PROVIDER) for symbol, _name in default_assets if symbol}

        if settings.market_board_default_only and default_keys:
            for asset in self.db.scalars(select(MarketAsset)):
                asset.enabled = (asset.symbol, asset.provider) in default_keys

        for symbol, name in default_assets:
            if symbol:
                exchange = symbol.split(".", 1)[0] if "." in symbol else ""
                self.add_asset(
                    MarketAssetCreate(
                        symbol=symbol,
                        name=name,
                        asset_type="stock",
                        exchange=exchange,
                        provider=self.PROVIDER,
                    )
                )
        self.db.commit()

    def add_asset(self, payload: MarketAssetCreate) -> MarketAsset:
        symbol = payload.symbol.upper()
        provider_name = self.PROVIDER
        asset = self.db.scalar(
            select(MarketAsset).where(MarketAsset.symbol == symbol, MarketAsset.provider == provider_name)
        )
        if asset is not None:
            asset.enabled = True
            asset.name = payload.name or asset.name
            asset.exchange = payload.exchange or asset.exchange
            asset.asset_type = payload.asset_type or asset.asset_type
            self.db.commit()
            return asset

        asset = MarketAsset(
            symbol=symbol,
            name=payload.name,
            asset_type=payload.asset_type,
            exchange=payload.exchange,
            provider=provider_name,
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def list_assets(self) -> list[MarketAsset]:
        return list(
            self.db.scalars(
                select(MarketAsset)
                .where(MarketAsset.enabled == True, MarketAsset.provider == self.PROVIDER)  # noqa: E712
                .order_by(MarketAsset.symbol)
            )
        )

    def get_asset(self, asset_id: int) -> MarketAsset:
        asset = self.db.get(MarketAsset, asset_id)
        if asset is None or asset.provider != self.PROVIDER:
            raise HTTPException(status_code=404, detail="Market asset not found")
        return asset

    def refresh_all(self, force: bool = False) -> int:
        self.ensure_default_assets()
        assets = list(
            self.db.scalars(
                select(MarketAsset).where(MarketAsset.enabled == True, MarketAsset.provider == self.PROVIDER)  # noqa: E712
            )
        )
        if not force:
            assets = [asset for asset in assets if MarketHoursService.is_open(asset.exchange)]

        refreshed = 0
        provider = get_market_data_provider(self.PROVIDER)
        quotes = provider.get_quotes([asset.symbol for asset in assets])
        quotes_by_symbol = {quote.symbol.upper(): quote for quote in quotes}
        for asset in assets:
            quote = quotes_by_symbol.get(asset.symbol.upper())
            if quote is None:
                continue
            self.add_quote(asset, quote)
            refreshed += 1
        self.db.commit()
        return refreshed

    def refresh_asset(self, asset: MarketAsset) -> MarketQuote:
        provider = get_market_data_provider(self.PROVIDER)
        quote = provider.get_quote(asset.symbol)
        row = self.add_quote(asset, quote)
        self.db.commit()
        return row

    def add_quote(self, asset: MarketAsset, quote) -> MarketQuote:
        row = MarketQuote(
            asset_id=asset.id,
            symbol=asset.symbol,
            provider=quote.provider,
            price=quote.price,
            currency=quote.currency,
            quote_time=quote.timestamp.replace(tzinfo=None),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        return row

    @staticmethod
    def _parse_default_asset(raw_value: str) -> tuple[str, str]:
        value = raw_value.strip()
        if not value:
            return "", ""
        if ":" in value:
            symbol, name = value.split(":", 1)
            return symbol.strip().upper(), name.strip()
        return value.upper(), ""

    def latest_quote(self, asset_id: int) -> MarketQuote | None:
        return self.db.scalar(
            select(MarketQuote).where(MarketQuote.asset_id == asset_id).order_by(MarketQuote.quote_time.desc())
        )

    def quote_history(self, asset_id: int, limit: int = 30) -> list[MarketQuote]:
        return list(
            self.db.scalars(
                select(MarketQuote)
                .where(MarketQuote.asset_id == asset_id)
                .order_by(MarketQuote.quote_time.desc())
                .limit(limit)
            )
        )[::-1]

    def aggregated_history(self, asset_id: int, timeframe: str, limit: int = 80) -> list[MarketQuote]:
        quotes = list(
            self.db.scalars(
                select(MarketQuote)
                .where(MarketQuote.asset_id == asset_id)
                .order_by(MarketQuote.quote_time.desc())
                .limit(max(limit * 8, limit))
            )
        )[::-1]
        if timeframe == "intraday":
            return quotes[-limit:]

        grouped: dict[tuple, MarketQuote] = {}
        for quote in quotes:
            if timeframe == "day":
                key = (quote.quote_time.date(),)
            elif timeframe == "week":
                iso = quote.quote_time.isocalendar()
                key = (iso.year, iso.week)
            elif timeframe == "month":
                key = (quote.quote_time.year, quote.quote_time.month)
            else:
                raise HTTPException(status_code=400, detail="Unsupported timeframe")
            grouped[key] = quote
        return list(grouped.values())[-limit:]
