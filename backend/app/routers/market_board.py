from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.market import MarketAssetCreate, MarketAssetRead, MarketBoardRow
from app.services.market_board import MarketBoardService
from app.services.market_hours import MarketHoursService

router = APIRouter()


@router.get("/assets", response_model=list[MarketAssetRead])
def list_assets(db: Session = Depends(get_db)):
    service = MarketBoardService(db)
    service.ensure_default_assets()
    assets = service.list_assets()
    return assets


@router.post("/assets", response_model=MarketAssetRead)
def add_asset(payload: MarketAssetCreate, db: Session = Depends(get_db)):
    return MarketBoardService(db).add_asset(payload)


@router.post("/refresh")
def refresh_quotes(db: Session = Depends(get_db)) -> dict[str, int]:
    refreshed = MarketBoardService(db).refresh_all(force=True)
    return {"refreshed": refreshed}


@router.get("/quotes", response_model=list[MarketBoardRow])
def board_quotes(limit: int = 30, db: Session = Depends(get_db)) -> list[MarketBoardRow]:
    service = MarketBoardService(db)
    service.ensure_default_assets()
    assets = service.list_assets()

    rows = []
    for asset in assets:
        latest = service.latest_quote(asset.id)
        history = service.quote_history(asset.id, limit=limit)
        rows.append(
            MarketBoardRow(
                asset=asset,
                latest_quote=latest,
                history=history,
                market_status=MarketHoursService.status_for_exchange(asset.exchange),
            )
        )
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
