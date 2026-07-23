from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.market_data.factory import get_market_data_provider
from app.models.simulation import SimulationTask, TradeLog
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.trading import OrderIntent, TradeLogRead
from app.simulation.engine import SimulationEngine

router = APIRouter()


@router.get("/{task_id}/trades", response_model=list[TradeLogRead])
def list_trades(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TradeLog]:
    _ensure_task(db, user.id, task_id)
    return list(db.scalars(select(TradeLog).where(TradeLog.task_id == task_id).order_by(TradeLog.traded_at.desc())))


@router.post("/{task_id}/paper-orders", response_model=TradeLogRead)
def submit_paper_order(
    task_id: int,
    payload: OrderIntent,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeLog:
    task = _ensure_task(db, user.id, task_id)
    market_data = get_market_data_provider()
    return SimulationEngine(db, market_data).execute_intent(task, payload)


def _ensure_task(db: Session, user_id: int, task_id: int) -> SimulationTask:
    task = db.scalar(
        select(SimulationTask)
        .where(SimulationTask.id == task_id, SimulationTask.user_id == user_id)
        .options(selectinload(SimulationTask.account))
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
