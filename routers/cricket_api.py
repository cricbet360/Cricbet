from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services import proexch_api


router = APIRouter(
    prefix="/api/cricket",
    tags=["Cricket"],
)


# =========================================================
# AUTH CHECK
# =========================================================

def _is_logged_in(
    request: Request,
):
    return (
        request.session.get("user_id")
        is not None
    )


# =========================================================
# MATCH LIST
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

    if not _is_logged_in(request):

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
            str(exc),
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
            dict,
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
                        False,
                    )
                ),

                "tv": bool(
                    item.get(
                        "tv",
                        False,
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

                "selection_id1": str(
                    item.get(
                        "selectionId1"
                    )
                    or ""
                ),

                "selection_id2": str(
                    item.get(
                        "selectionId2"
                    )
                    or ""
                ),

                "selection_id3": str(
                    item.get(
                        "selectionId3"
                    )
                    or ""
                ),
            }
        )

    print(
        "PROEXCH MATCHES:",
        len(result),
    )

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
    gameId: str,
    marketId: str = "",
):

    print()
    print("========================================")
    print("CRICBET ODDS API")
    print("GAME ID:", gameId)
    print("MARKET ID:", marketId)
    print("========================================")

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
                "odds": None,
            },
            status_code=401,
        )

    try:

        odds = proexch_api.get_odds(
            game_id=gameId,
            market_id=marketId,
        )

    except Exception as exc:

        print(
            "PROEXCH ODDS ERROR:",
            str(exc),
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "odds": None,
            },
            status_code=502,
        )

    return {
        "success": True,
        "game_id": str(gameId),
        "market_id": str(marketId),
        "odds": odds,
    }


# =========================================================
# SINGLE MATCH
# =========================================================

@router.get("/match/{game_id}")
async def cricket_match(
    request: Request,
    game_id: str,
):

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        match = (
            proexch_api.get_match(
                game_id
            )
        )

    except Exception as exc:

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )

    if match is None:

        return JSONResponse(
            {
                "success": False,
                "error": "Match not found",
            },
            status_code=404,
        )

    return {
        "success": True,
        "match": match,
    }


# =========================================================
# COMPLETE MATCH
# =========================================================

@router.get("/complete/{game_id}")
async def complete_match(
    request: Request,
    game_id: str,
    marketId: str = "",
):

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        match = (
            proexch_api.get_match(
                game_id
            )
        )

        if match is None:

            return JSONResponse(
                {
                    "success": False,
                    "error": "Match not found",
                },
                status_code=404,
            )

        market_id = (
            marketId
            or match.get("marketId")
            or ""
        )

        if not market_id:

            return {
                "success": True,
                "match": match,
                "odds": {},
                "match_result": None,
                "bookmaker_result": None,
                "fancy_results": [],
            }

        data = (
            proexch_api.get_complete_match_data(
                game_id,
                market_id,
            )
        )

        return {
            "success": True,
            "match": match,
            **data,
        }

    except Exception as exc:

        print(
            "COMPLETE MATCH ERROR:",
            str(exc),
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )