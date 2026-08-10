from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.wallet import Wallet

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/wallet")
async def wallet_page(
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

    wallet = db.query(Wallet).filter(
        Wallet.user_id == user.id
    ).first()

    if wallet is None:
        wallet = Wallet(
            user_id=user.id,
            balance=0.0,
            exposure=0.0
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    return templates.TemplateResponse(
        "wallet.html",
        {
            "request": request,
            "user": user,
            "wallet": wallet
        }
    )