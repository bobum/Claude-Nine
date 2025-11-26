from fastapi import APIRouter

from ..personas import get_all_personas

router = APIRouter()


@router.get("/")
def list_personas():
    """Get all available agent personas"""
    return {"personas": get_all_personas()}
