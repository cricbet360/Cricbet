from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from services.odds_api import get_cricket_matches


router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        request.session.clear()

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # Fetch cricket matches from The Odds API
    matches = get_cricket_matches()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "matches": matches
        }
    )