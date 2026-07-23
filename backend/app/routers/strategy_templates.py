from fastapi import APIRouter

from app.strategies.templates import STRATEGY_TEMPLATES

router = APIRouter()


@router.get("")
def list_strategy_templates() -> list[dict]:
    return STRATEGY_TEMPLATES
