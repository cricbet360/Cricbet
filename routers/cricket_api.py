from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from services import proexch_api


router = APIRouter(
    prefix="/api/cricket",
    tags=["Cricket"],
)


# =========================================================
# AUTHENTICATION
# =========================================================

def get_user_id(request: Request):

    return request.session.get(
        "user_id"
    )


# =========================================================
# MATCHES
# =========================================================

@router.get("/matches")
async def cricket_matches(
    request: Request,
):

    print()
    print("========================================")
    print("CRICBET CRICKET MATCH API")
    print("GET /api/cricket/matches")
    print("========================================")

    user_id = get_user_id(request)

    print(
        "SESSION USER ID:",
        user_id
    )

    if not user_id:

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
                "matches": [],
            },
            status_code=401,
        )

    try:

        matches = (
            proexch_api.get_matches()
        )

    except Exception as exc:

        print(
            "PROEXCH MATCH ERROR:",
            str(exc)
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "matches": [],
            },
            status_code=502,
        )

    result = []

    for item in matches:

        if not isinstance(
            item,
            dict
        ):
            continue

        game_id = item.get(
            "gameId"
        )

        if game_id is None:
            continue

        game_id = str(
            game_id
        ).strip()

        if not game_id:
            continue

        market_id = item.get(
            "marketId"
        )

        event_id = item.get(
            "eventId"
        )

        result.append(
            {
                "game_id": game_id,

                "market_id": (
                    str(market_id)
                    if market_id is not None
                    else ""
                ),

                "event_id": (
                    str(event_id)
                    if event_id is not None
                    else ""
                ),

                "event_name": str(
                    item.get(
                        "eventName"
                    )
                    or "Cricket Match"
                ),

                "event_time": str(
                    item.get(
                        "eventTime"
                    )
                    or ""
                ),

                "in_play": bool(
                    item.get(
                        "inPlay",
                        False
                    )
                ),

                "tv": bool(
                    item.get(
                        "tv",
                        False
                    )
                ),

                "team1": str(
                    item.get(
                        "runnerName1"
                    )
                    or "Team 1"
                ),

                "team2": str(
                    item.get(
                        "runnerName2"
                    )
                    or "Team 2"
                ),

                "team3": str(
                    item.get(
                        "runnerName3"
                    )
                    or "The Draw"
                ),

                "selection_id1": item.get(
                    "selectionId1"
                ),

                "selection_id2": item.get(
                    "selectionId2"
                ),

                "selection_id3": item.get(
                    "selectionId3"
                ),
            }
        )

    print(
        "PROEXCH MATCHES:",
        len(result)
    )

    for match in result[:10]:

        print(
            "GAME:",
            match["game_id"],
            "| MARKET:",
            match["market_id"],
            "| EVENT:",
            match["event_name"],
        )

    print("========================================")

    return {
        "success": True,
        "matches": result,
    }


# =========================================================
# ODDS
# =========================================================

@router.get("/odds")
async def cricket_odds(
    request: Request,
    gameId: str = Query(...),
):

    print()
    print("========================================")
    print("CRICBET ODDS API")
    print("GAME ID:", gameId)
    print("========================================")

    user_id = get_user_id(request)

    if not user_id:

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    game_id = str(
        gameId
    ).strip()

    if not game_id:

        return JSONResponse(
            {
                "success": False,
                "error": "gameId is required",
            },
            status_code=400,
        )

    try:

        odds = proexch_api.get_odds(
            game_id
        )

    except Exception as exc:

        print(
            "PROEXCH ODDS ERROR:",
            str(exc)
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "game_id": game_id,
            },
            status_code=502,
        )

    return {
        "success": True,
        "game_id": game_id,
        "odds": odds,
    }


# =========================================================
# MATCH RESULT
# =========================================================

@router.get("/result/match")
async def match_result(
    request: Request,
    marketId: str = Query(...),
):

    user_id = get_user_id(request)

    if not user_id:

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        result = (
            proexch_api.get_match_result(
                marketId
            )
        )

        return {
            "success": True,
            "market_id": str(
                marketId
            ),
            "result": result,
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )


# =========================================================
# BOOKMAKER RESULT
# =========================================================

@router.get("/result/bookmaker")
async def bookmaker_result(
    request: Request,
    marketId: str = Query(...),
):

    user_id = get_user_id(request)

    if not user_id:

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        result = (
            proexch_api.get_bookmaker_result(
                marketId
            )
        )

        return {
            "success": True,
            "market_id": str(
                marketId
            ),
            "result": result,
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )


# =========================================================
# SINGLE FANCY RESULT
# =========================================================

@router.get("/result/fancy")
async def fancy_result(
    request: Request,
    marketId: str = Query(...),
):

    user_id = get_user_id(request)

    if not user_id:

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        result = (
            proexch_api.get_fancy_result_by_market_id(
                marketId
            )
        )

        return {
            "success": True,
            "market_id": str(
                marketId
            ),
            "result": result,
        }

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )


# =========================================================
# COMPLETE MATCH DATA
# =========================================================

@router.get("/complete")
async def complete_match(
    request: Request,
    gameId: str = Query(...),
    marketId: str = Query(...),
):

    user_id = get_user_id(request)

    if not user_id:

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    game_id = str(
        gameId
    ).strip()

    market_id = str(
        marketId
    ).strip()

    if not game_id:

        return JSONResponse(
            {
                "success": False,
                "error": "gameId is required",
            },
            status_code=400,
        )

    if not market_id:

        return JSONResponse(
            {
                "success": False,
                "error": "marketId is required",
            },
            status_code=400,
        )

    try:

        data = (
            proexch_api.get_complete_match_data(
                game_id,
                market_id,
            )
        )

        return {
            "success": True,
            **data,
        }

    except Exception as exc:

        print(
            "COMPLETE MATCH ERROR:",
            str(exc)
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )