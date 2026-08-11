from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.bet import Bet
from models.bet_selection import BetSelection

from services.bex_api import get_market_book


router = APIRouter(
    prefix="/bets",
    tags=["bets"],
)


# ==========================================================
# BEX MARKET BOOK HELPERS
# ==========================================================

def get_market_from_response(
    market_book,
    market_id,
):
    """
    Find one market from a BEX listMarketBook response.
    """

    if not isinstance(
        market_book,
        dict
    ):
        return None

    data = market_book.get(
        "data",
        []
    )

    if not isinstance(
        data,
        list
    ):
        return None

    for market in data:

        if not isinstance(
            market,
            dict
        ):
            continue

        if str(
            market.get("marketId")
        ) == str(market_id):

            return market

    # If BEX returned only one market,
    # use it as a fallback.
    if len(data) == 1:

        if isinstance(
            data[0],
            dict
        ):
            return data[0]

    return None


def get_runner_price(
    market,
    selection_id,
    side="BACK",
):
    """
    Get the current live price for one runner
    from an already-fetched market book.
    """

    if not isinstance(
        market,
        dict
    ):
        return None

    # ------------------------------------------------------
    # MARKET STATUS
    # ------------------------------------------------------

    if market.get("status") != "OPEN":
        return None

    runners = market.get(
        "runners",
        []
    )

    if not isinstance(
        runners,
        list
    ):
        return None

    # ------------------------------------------------------
    # FIND RUNNER
    # ------------------------------------------------------

    for runner in runners:

        if not isinstance(
            runner,
            dict
        ):
            continue

        if str(
            runner.get("selectionId")
        ) != str(selection_id):

            continue

        # --------------------------------------------------
        # RUNNER STATUS
        # --------------------------------------------------

        if runner.get(
            "status"
        ) != "ACTIVE":

            return None

        # --------------------------------------------------
        # EXCHANGE
        # --------------------------------------------------

        exchange = runner.get(
            "ex",
            {}
        )

        if not isinstance(
            exchange,
            dict
        ):
            return None

        # --------------------------------------------------
        # BACK / LAY
        # --------------------------------------------------

        if side == "BACK":

            prices = exchange.get(
                "availableToBack",
                []
            )

        else:

            prices = exchange.get(
                "availableToLay",
                []
            )

        if not isinstance(
            prices,
            list
        ):
            return None

        if not prices:
            return None

        first_price = prices[0]

        if not isinstance(
            first_price,
            dict
        ):
            return None

        price = first_price.get(
            "price"
        )

        try:

            return float(price)

        except (
            TypeError,
            ValueError,
        ):

            return None

    return None


# ==========================================================
# PLACE BET
# ==========================================================

@router.post("/place")
async def place_bet(
    request: Request,
    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message":
                    "You must be logged in.",
            },
        )

    # ------------------------------------------------------
    # FIND USER
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        request.session.clear()

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message":
                    "User not found.",
            },
        )

    # ------------------------------------------------------
    # READ REQUEST
    # ------------------------------------------------------

    try:

        data = await request.json()

    except Exception:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid request.",
            },
        )

    if not isinstance(
        data,
        dict
    ):

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid request data.",
            },
        )

    selections = data.get(
        "selections",
        []
    )

    stake = data.get(
        "stake"
    )

    # ------------------------------------------------------
    # VALIDATE SELECTIONS
    # ------------------------------------------------------

    if not isinstance(
        selections,
        list
    ) or not selections:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "No selections provided.",
            },
        )

    # ------------------------------------------------------
    # VALIDATE STAKE
    # ------------------------------------------------------

    try:

        stake = float(stake)

    except (
        TypeError,
        ValueError,
    ):

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid stake.",
            },
        )

    if stake <= 0:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Stake must be greater than zero.",
            },
        )

    # ------------------------------------------------------
    # CHECK BALANCE
    # ------------------------------------------------------

    try:

        current_balance = float(
            user.balance or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        current_balance = 0.0

    if current_balance < stake:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Insufficient wallet balance.",
            },
        )

    # ======================================================
    # VALIDATE REQUEST SELECTIONS
    # ======================================================

    validated_selections = []

    market_ids = []

    for selection in selections:

        if not isinstance(
            selection,
            dict
        ):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Invalid selection.",
                },
            )

        # --------------------------------------------------
        # IDS
        # --------------------------------------------------

        market_id = selection.get(
            "marketId"
        )

        selection_id = selection.get(
            "selectionId"
        )

        event_id = selection.get(
            "eventId"
        )

        runner_name = selection.get(
            "runnerName"
        )

        event_name = selection.get(
            "eventName"
        )

        market_name = selection.get(
            "marketName"
        )

        side = str(
            selection.get(
                "side",
                "BACK"
            )
        ).upper()

        # --------------------------------------------------
        # MARKET ID
        # --------------------------------------------------

        if not market_id:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Market ID missing.",
                },
            )

        # --------------------------------------------------
        # SELECTION ID
        # --------------------------------------------------

        if not selection_id:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Selection ID missing.",
                },
            )

        # --------------------------------------------------
        # SIDE
        # --------------------------------------------------

        if side not in (
            "BACK",
            "LAY",
        ):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Invalid bet side.",
                },
            )

        # --------------------------------------------------
        # CONVERT IDS
        # --------------------------------------------------

        market_id = str(
            market_id
        )

        selection_id = str(
            selection_id
        )

        if event_id is not None:

            event_id = str(
                event_id
            )

        # --------------------------------------------------
        # SAVE REQUEST DATA
        # --------------------------------------------------

        validated_selections.append({

            "market_id":
                market_id,

            "selection_id":
                selection_id,

            "event_id":
                event_id,

            "runner_name":
                str(
                    runner_name
                    or "Unknown"
                ),

            "event_name":
                str(
                    event_name
                    or "Cricket Match"
                ),

            "market_name":
                str(
                    market_name
                    or "Market"
                ),

            "side":
                side,

        })

        # --------------------------------------------------
        # UNIQUE MARKET IDS
        # --------------------------------------------------

        if market_id not in market_ids:

            market_ids.append(
                market_id
            )

    # ======================================================
    # BEX MARKET BOOK
    # ======================================================

    try:

        market_book = get_market_book(
            market_ids
        )

    except Exception as e:

        print(
            "BEX market book error:",
            repr(e),
        )

        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message":
                    "Live odds are temporarily unavailable.",
            },
        )

    # ======================================================
    # VALIDATE LIVE ODDS
    # ======================================================

    total_odds = 1.0

    prices_used = []

    for selection in validated_selections:

        market_id = selection[
            "market_id"
        ]

        selection_id = selection[
            "selection_id"
        ]

        side = selection[
            "side"
        ]

        # --------------------------------------------------
        # FIND MARKET
        # --------------------------------------------------

        market = get_market_from_response(
            market_book,
            market_id
        )

        if market is None:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Selected market is no longer available.",
                },
            )

        # --------------------------------------------------
        # GET LIVE PRICE
        # --------------------------------------------------

        live_price = get_runner_price(
            market,
            selection_id,
            side,
        )

        if live_price is None:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Selected odds are no longer available.",
                },
            )

        if live_price <= 1.0:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Invalid live odds.",
                },
            )

        # --------------------------------------------------
        # TOTAL ODDS
        # --------------------------------------------------

        total_odds *= live_price

        # --------------------------------------------------
        # STORE ACTUAL PRICE USED
        # --------------------------------------------------

        prices_used.append({

            "marketId":
                market_id,

            "selectionId":
                selection_id,

            "side":
                side,

            "price":
                live_price,

        })

    # ======================================================
    # CALCULATE POTENTIAL WIN
    # ======================================================

    potential_win = (
        stake * total_odds
    )

    # ======================================================
    # CREATE BET
    # ======================================================

    bet = Bet(

        user_id=user.id,

        stake=stake,

        total_odds=total_odds,

        potential_win=potential_win,

        status="pending",

    )

    db.add(
        bet
    )

    # ======================================================
    # CREATE BET SELECTIONS
    # ======================================================

    for index, selection in enumerate(
        validated_selections
    ):

        # ----------------------------------------------
        # GET LIVE PRICE USED
        # ----------------------------------------------

        live_price = prices_used[index][
            "price"
        ]

        bet_selection = BetSelection(

            bet=bet,

            market_id=
                selection[
                    "market_id"
                ],

            event_id=
                selection[
                    "event_id"
                ],

            selection_id=
                selection[
                    "selection_id"
                ],

            runner_name=
                selection[
                    "runner_name"
                ],

            side=
                selection[
                    "side"
                ],

            price=live_price,

            market_name=
                selection[
                    "market_name"
                ],

            event_name=
                selection[
                    "event_name"
                ],

        )

        db.add(
            bet_selection
        )

    # ======================================================
    # UPDATE BALANCE
    # ======================================================

    user.balance = (
        current_balance - stake
    )

    # ======================================================
    # DATABASE COMMIT
    # ======================================================

    try:

        db.commit()

        db.refresh(
            bet
        )

    except Exception as e:

        db.rollback()

        print(
            "Bet database error:",
            repr(e),
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message":
                    "Could not place bet.",
            },
        )

    # ======================================================
    # SUCCESS
    # ======================================================

    return {

        "success":
            True,

        "message":
            "Bet placed successfully.",

        "bet_id":
            bet.id,

        "stake":
            round(
                stake,
                2
            ),

        "total_odds":
            round(
                total_odds,
                2
            ),

        "potential_win":
            round(
                potential_win,
                2
            ),

        "balance":
            round(
                float(
                    user.balance
                ),
                2
            ),

        "prices":
            prices_used,

    }


# ==========================================================
# MY BETS
# ==========================================================

@router.get("/my-bets")
async def my_bets(
    request: Request,
    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message":
                    "You must be logged in.",
            },
        )

    # ------------------------------------------------------
    # GET USER
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        request.session.clear()

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message":
                    "User not found.",
            },
        )

    # ======================================================
    # GET USER BETS
    # ======================================================

    bets = (
        db.query(Bet)
        .filter(
            Bet.user_id == user.id
        )
        .order_by(
            Bet.created_at.desc()
        )
        .all()
    )

    # ======================================================
    # FORMAT BETS
    # ======================================================

    result = []

    for bet in bets:

        bet_selections = []

        # --------------------------------------------------
        # SELECTIONS
        # --------------------------------------------------

        for selection in bet.selections:

            bet_selections.append({

                "id":
                    selection.id,

                "market_id":
                    selection.market_id,

                "event_id":
                    selection.event_id,

                "selection_id":
                    selection.selection_id,

                "runner_name":
                    selection.runner_name,

                "side":
                    selection.side,

                "price":
                    round(
                        float(
                            selection.price or 0
                        ),
                        2
                    ),

                "market_name":
                    selection.market_name,

                "event_name":
                    selection.event_name,

            })

        # --------------------------------------------------
        # BET
        # --------------------------------------------------

        result.append({

            "id":
                bet.id,

            "stake":
                round(
                    float(
                        bet.stake or 0
                    ),
                    2
                ),

            "total_odds":
                round(
                    float(
                        bet.total_odds or 0
                    ),
                    2
                ),

            "potential_win":
                round(
                    float(
                        bet.potential_win or 0
                    ),
                    2
                ),

            "status":
                bet.status or "pending",

            "created_at": (

                bet.created_at.isoformat()

                if bet.created_at

                else None
            ),

            "selections":
                bet_selections,

        })

    # ======================================================
    # RESPONSE
    # ======================================================

    return {

        "success":
            True,

        "balance":
            round(
                float(
                    user.balance or 0
                ),
                2
            ),

        "count":
            len(result),

        "bets":
            result,

    }