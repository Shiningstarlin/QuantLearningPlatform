from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.simulation import ControlEvent, PaperAccount, SimulationTask
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.simulation import (
    ControlRequest,
    InvestmentProcessCreate,
    ManualExposureUpdate,
    PaperAccountCreate,
    PaperAccountRead,
    SimulationFeeSchedulesRead,
    SimulationTaskCreate,
    SimulationTaskRead,
)
from app.services.fees import FutuFeeService
from app.services.simulation_tasks import SimulationTaskService

router = APIRouter()


@router.get("/accounts", response_model=list[PaperAccountRead])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PaperAccount]:
    return SimulationTaskService(db).list_accounts(user.id)


@router.post("/accounts", response_model=PaperAccountRead)
def create_account(
    payload: PaperAccountCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperAccount:
    return SimulationTaskService(db).create_account(user.id, payload)


@router.post("/accounts/{account_id}/processes", response_model=SimulationTaskRead)
def create_process(
    account_id: int,
    payload: InvestmentProcessCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationTask:
    return SimulationTaskService(db).create_process(user.id, account_id, payload)


@router.get("/fees", response_model=SimulationFeeSchedulesRead)
def fee_schedules() -> SimulationFeeSchedulesRead:
    return FutuFeeService.schedule()


@router.get("", response_model=list[SimulationTaskRead])
def list_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SimulationTask]:
    stmt = (
        select(SimulationTask)
        .where(SimulationTask.user_id == user.id)
        .options(selectinload(SimulationTask.account))
        .order_by(SimulationTask.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.post("", response_model=SimulationTaskRead)
def create_task(
    payload: SimulationTaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationTask:
    task = SimulationTaskService(db).create_task(user_id=user.id, payload=payload)
    return task


@router.get("/{task_id}", response_model=SimulationTaskRead)
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SimulationTask:
    task = db.scalar(
        select(SimulationTask)
        .where(SimulationTask.id == task_id, SimulationTask.user_id == user.id)
        .options(selectinload(SimulationTask.account))
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/control", response_model=SimulationTaskRead)
def control_task(
    task_id: int,
    payload: ControlRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationTask:
    task = SimulationTaskService(db).apply_control(user_id=user.id, task_id=task_id, payload=payload)
    return task


@router.post("/{task_id}/manual-exposure", response_model=SimulationTaskRead)
def update_manual_exposure(
    task_id: int,
    payload: ManualExposureUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationTask:
    return SimulationTaskService(db).update_manual_exposure(user.id, task_id, payload)


@router.get("/{task_id}/events")
def list_control_events(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    task = db.scalar(select(SimulationTask).where(SimulationTask.id == task_id, SimulationTask.user_id == user.id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    events = db.scalars(select(ControlEvent).where(ControlEvent.task_id == task_id).order_by(ControlEvent.created_at.desc()))
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "amount": event.amount,
            "note": event.note,
            "created_at": event.created_at,
        }
        for event in events
    ]
