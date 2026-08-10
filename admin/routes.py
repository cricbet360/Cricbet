from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from models.admin import Admin

router = APIRouter(prefix="/admin")

templates = Jinja2Templates(directory="templates")


@router.get("/dashboard")
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    admin_id = request.session.get("admin_id")

    if not admin_id:
        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    admin = db.query(Admin).filter(
        Admin.id == admin_id
    ).first()

    if not admin:
        request.session.clear()
        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "admin": admin
        }
    )