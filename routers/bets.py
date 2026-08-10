from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.bet import Bet

from services.bex_api import get_market_book


router = APIRouter(
    prefix="/bets",
    tags=["bets"]
)


def get_live_price(
    market_id,
    selection_id,
    side="BACK"
):
    """
    Get the current live price for a selection
    from the BEX market book.
    """

    market_book = get_market_book(market_id)

    if not isinstance(market_book, dict):
        return None

    data = market_book.get("data", [])

    if not data:
        return None

    market = data[0]

    if market.get("status") != "OPEN":
        return None

    for runner in market.get("runners", []):

        if str(runner.get("selectionId")) != str(selection_id):
            continue

        if runner.get("status") != "ACTIVE":
            return None

        ex = runner.get("ex", {})

        if side == "BACK":
            prices = ex.get("availableToBack", [])
        else:
            prices = ex.get("availableToLay", [])

        if not prices:
            return None

        try:
            return float(prices[0]["price"])
        except (KeyError, TypeError, ValueError):
            return None

    return None


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

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

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

    if user.balance < stake:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Insufficient wallet balance."
            }
        )

    total_odds = 1.0

    for selection in selections:

        market_id = selection.get("marketId")
        selection_id = selection.get("selectionId")

        side = selection.get(
            "side",
            "BACK"
        ).upper()

        if not market_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Market ID missing."
                }
            )

        if not selection_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Selection ID missing."
                }
            )

        if side not in ("BACK", "LAY"):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Invalid bet side."
                }
            )

        try:

            live_price = get_live_price(
                market_id,
                selection_id,
                side
            )

        except Exception as e:

            print(
                f"BEX odds error: {e}"
            )

            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "Live odds are temporarily unavailable."
                }
            )

        if live_price is None:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": (
                        "Selected market or odds are "
                        "no longer available."
                    )
                }
            )

        total_odds *= live_price

    potential_win = stake * total_odds

    user.balance -= stake

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

    except Exception as e:

        db.rollback()

        print(
            f"Bet database error: {e}"
        )

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