from fastapi import APIRouter
from services.sportmonks import get_teams

router = APIRouter(
    prefix="/api",
    tags=["SportMonks"]
)


@router.get("/teams")
def teams():
    return get_teams()