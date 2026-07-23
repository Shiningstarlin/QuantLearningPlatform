from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.backtest import BacktestRun, BacktestTask
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.backtest import (
    BacktestAssetRead,
    BacktestBatchCreate,
    BacktestBatchRead,
    BacktestComparisonRead,
    BacktestCreate,
    BacktestDetailRead,
    BacktestPreviewRead,
    BacktestRunRead,
    BacktestTaskRead,
)
from app.services.backtest import BacktestService

router = APIRouter()


@router.get("", response_model=list[BacktestTaskRead])
def list_backtests(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BacktestTask]:
    return BacktestService(db).list_tasks(user.id)


@router.get("/assets", response_model=list[BacktestAssetRead])
def list_backtest_assets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BacktestAssetRead]:
    return BacktestService(db).list_assets()


@router.post("", response_model=BacktestRunRead)
def create_backtest(
    payload: BacktestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacktestRun:
    return BacktestService(db).create_and_run(user.id, payload)


@router.post("/batch", response_model=BacktestBatchRead)
def create_backtest_batch(
    payload: BacktestBatchCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacktestBatchRead:
    task, runs = BacktestService(db).create_batch_and_run(user.id, payload)
    return BacktestBatchRead(task=task, runs=runs)


@router.get("/preview", response_model=BacktestPreviewRead)
def preview_backtest_history(
    market_asset_id: int | None = Query(default=None, gt=0),
    yfinance_symbol: str | None = Query(default=None),
    start_date: date = Query(),
    end_date: date = Query(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacktestPreviewRead:
    return BacktestService(db).preview_history(market_asset_id, yfinance_symbol, start_date, end_date)


@router.get("/compare", response_model=BacktestComparisonRead)
def compare_backtests(
    ids: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacktestComparisonRead:
    parsed_ids = []
    for raw_id in ids.split(","):
        raw_id = raw_id.strip()
        if raw_id.isdigit():
            parsed_ids.append(int(raw_id))
    runs = BacktestService(db).get_runs_for_comparison(user.id, parsed_ids)
    return BacktestComparisonRead(runs=runs)


@router.get("/{backtest_id}", response_model=BacktestDetailRead)
def get_backtest(
    backtest_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacktestDetailRead:
    run = BacktestService(db).get_run(user.id, backtest_id)
    equity_points = sorted(run.equity_points, key=lambda point: point.point_date)
    trades = sorted(run.trades, key=lambda trade: trade.traded_on)
    asset_metrics = BacktestService.asset_metrics_from_points(equity_points)
    sibling_runs = sorted(run.task.runs, key=lambda sibling: sibling.strategy_key) if run.task else []
    return BacktestDetailRead(
        task=run.task,
        run=run,
        sibling_runs=sibling_runs,
        equity_points=equity_points,
        trades=trades,
        asset_metrics=asset_metrics,
    )
