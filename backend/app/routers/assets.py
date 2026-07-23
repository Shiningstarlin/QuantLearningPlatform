from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.asset import WatchAsset
from app.models.simulation import SimulationTask
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.assets import WatchAssetCreate, WatchAssetRead

router = APIRouter()


@router.get("/{task_id}/assets", response_model=list[WatchAssetRead])
def list_assets(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WatchAsset]:
    _ensure_task(db, user.id, task_id)
    return list(db.scalars(select(WatchAsset).where(WatchAsset.task_id == task_id).order_by(WatchAsset.symbol)))


@router.post("/{task_id}/assets", response_model=WatchAssetRead)
def add_asset(
    task_id: int,
    payload: WatchAssetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchAsset:
    _ensure_task(db, user.id, task_id)
    asset = WatchAsset(task_id=task_id, **payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _ensure_task(db: Session, user_id: int, task_id: int) -> SimulationTask:
    task = db.scalar(select(SimulationTask).where(SimulationTask.id == task_id, SimulationTask.user_id == user_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
