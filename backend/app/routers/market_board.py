from datetime import date, datetime, timedelta, timezone
from time import monotonic

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.insights import FactorInsightsRead
from app.schemas.market import MarketAssetCreate, MarketAssetRead, MarketBoardRow
from app.services.factor_insights import FactorInsightsService
from app.services.market_board import MarketBoardService
from app.services.market_hours import MarketHoursService

router = APIRouter()
_QUOTE_CACHE_TTL_SECONDS = 8
_QUOTE_CACHE: dict[int, tuple[float, list[MarketBoardRow]]] = {}


@router.get("/assets", response_model=list[MarketAssetRead])
def list_assets(db: Session = Depends(get_db)):
    service = MarketBoardService(db)
    service.ensure_default_assets()
    assets = service.list_assets()
    return assets


@router.post("/assets", response_model=MarketAssetRead)
def add_asset(payload: MarketAssetCreate, db: Session = Depends(get_db)):
    _QUOTE_CACHE.clear()
    return MarketBoardService(db).add_asset(payload)


@router.get("/quotes", response_model=list[MarketBoardRow])
def board_quotes(limit: int = 30, db: Session = Depends(get_db)) -> list[MarketBoardRow]:
    normalized_limit = max(1, min(limit, 120))
    cached = _QUOTE_CACHE.get(normalized_limit)
    if cached and cached[0] > monotonic():
        return cached[1]

    service = MarketBoardService(db)
    service.ensure_default_assets()
    assets = service.list_assets()
    asset_ids = [asset.id for asset in assets]
    latest_by_asset = service.latest_quotes_by_asset(asset_ids)
    history_by_asset = service.quote_history_by_asset(asset_ids, limit=normalized_limit)

    rows = []
    for asset in assets:
        rows.append(
            MarketBoardRow(
                asset=asset,
                latest_quote=latest_by_asset.get(asset.id),
                history=history_by_asset.get(asset.id, []),
                market_status=MarketHoursService.status_for_exchange(asset.exchange),
            )
        )
    _QUOTE_CACHE[normalized_limit] = (monotonic() + _QUOTE_CACHE_TTL_SECONDS, rows)
    return rows


@router.get("/assets/{asset_id}/history", response_model=MarketBoardRow)
def asset_history(asset_id: int, timeframe: str = "intraday", limit: int = 80, db: Session = Depends(get_db)) -> MarketBoardRow:
    service = MarketBoardService(db)
    asset = service.get_asset(asset_id)
    latest = service.latest_quote(asset.id)
    history = service.aggregated_history(asset.id, timeframe=timeframe, limit=limit)
    return MarketBoardRow(
        asset=asset,
        latest_quote=latest,
        history=history,
        market_status=MarketHoursService.status_for_exchange(asset.exchange),
    )


@router.get("/assets/{asset_id}/insights", response_model=FactorInsightsRead)
def asset_factor_insights(
    asset_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    days: int = 7,
    db: Session = Depends(get_db),
) -> FactorInsightsRead:
    resolved_end = end_date or datetime.now(timezone.utc).date()
    resolved_start = start_date or (resolved_end - timedelta(days=max(1, min(days, 365)) - 1))
    return FactorInsightsService(db).get_insights(asset_id, resolved_start, resolved_end)
