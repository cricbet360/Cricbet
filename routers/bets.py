from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.bet import Bet


router = APIRouter(
    prefix="/bets",
    tags=["bets"]
)


@router.post("/place")
async def place_bet(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.session.get("user_id")

    if not user_id:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "You must be logged in."
            }
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "User not found."
            }
        )

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Invalid request."
            }
        )

    selections = data.get("selections", [])
    stake = data.get("stake")

    if not selections:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "No selections provided."
            }
        )

    try:
        stake = float(stake)
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Invalid stake."
            }
        )

    if stake <= 0:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Stake must be greater than zero."
            }
        )

    total_odds = 1.0

    for selection in selections:

        try:
            price = float(selection["price"])
        except (KeyError, TypeError, ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Invalid odds."
                }
            )

        if price <= 1:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Invalid odds value."
                }
            )

        total_odds *= price

    potential_win = stake * total_odds

    # Check existing user balance
    if user.balance < stake:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Insufficient wallet balance."
            }
        )

    # Deduct stake
    user.balance -= stake

    # Create bet
    bet = Bet(
        user_id=user.id,
        stake=stake,
        total_odds=total_odds,
        potential_win=potential_win,
        status="pending"
    )

    db.add(bet)

    try:

        db.commit()
        db.refresh(bet)

    except Exception:

        db.rollback()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Could not place bet."
            }
        )

    return {
        "success": True,
        "message": "Bet placed successfully.",
        "bet_id": bet.id,
        "stake": round(stake, 2),
        "total_odds": round(total_odds, 2),
        "potential_win": round(potential_win, 2),
        "balance": round(user.balance, 2)
    }