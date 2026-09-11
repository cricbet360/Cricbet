from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services import proexch_api


router = APIRouter(
    prefix="/api/cricket",
    tags=["Cricket"],
)


# =========================================================
# AUTHENTICATION
# =========================================================

def _is_logged_in(request: Request):
    return request.session.get("user_id") is not None


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

    user_id = request.session.get(
        "user_id"
    )

    print(
        "SESSION USER ID:",
        user_id,
    )

    if not user_id:

        print(
            "CRICKET API: USER NOT AUTHENTICATED"
        )

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
                "matches": [],
            },
            status_code=401,
        )

    try:

        matches = proexch_api.get_matches()

    except Exception as exc:

        print()
        print("========================================")
        print("PROEXCH MATCH LIST ERROR")
        print(str(exc))
        print("========================================")
        print()

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

        if not isinstance(item, dict):
            continue

        game_id = item.get("gameId")

        if game_id is None:
            continue

        game_id = str(game_id).strip()

        if not game_id:
            continue

        market_id = item.get(
            "marketId"
        )

        event_id = item.get(
            "eventId"
        )

        event_name = (
            item.get("eventName")
            or "Cricket Match"
        )

        event_time = (
            item.get("eventTime")
            or ""
        )

        in_play = bool(
            item.get(
                "inPlay",
                False,
            )
        )

        tv = bool(
            item.get(
                "tv",
                False,
            )
        )

        team1 = (
            item.get("runnerName1")
            or "Team 1"
        )

        team2 = (
            item.get("runnerName2")
            or "Team 2"
        )

        team3 = (
            item.get("runnerName3")
            or "The Draw"
        )

        selection_id1 = item.get(
            "selectionId1"
        )

        selection_id2 = item.get(
            "selectionId2"
        )

        selection_id3 = item.get(
            "selectionId3"
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
                    event_name
                ),

                "event_time": str(
                    event_time
                ),

                "in_play": in_play,

                "tv": tv,

                "team1": str(
                    team1
                ),

                "team2": str(
                    team2
                ),

                "team3": str(
                    team3
                ),

                "selection_id1": (
                    str(selection_id1)
                    if selection_id1 is not None
                    else ""
                ),

                "selection_id2": (
                    str(selection_id2)
                    if selection_id2 is not None
                    else ""
                ),

                "selection_id3": (
                    str(selection_id3)
                    if selection_id3 is not None
                    else ""
                ),
            }
        )

    print(
        "PROEXCH MATCHES:",
        len(result),
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
    print()

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
):

    print()
    print("========================================")
    print("CRICBET ODDS API")
    print("GAME ID:", gameId)
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

    game_id = str(
        gameId
    ).strip()

    if not game_id:

        return JSONResponse(
            {
                "success": False,
                "error": "gameId is required",
                "odds": None,
            },
            status_code=400,
        )

    try:

        odds = proexch_api.get_odds(
            game_id
        )

    except Exception as exc:

        print()
        print("========================================")
        print("PROEXCH ODDS ERROR")
        print(str(exc))
        print("========================================")
        print()

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
        "game_id": game_id,
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

    print()
    print("========================================")
    print("CRICBET SINGLE MATCH API")
    print("GAME ID:", game_id)
    print("========================================")

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        match = proexch_api.get_match(
            game_id
        )

    except Exception as exc:

        print(
            "PROEXCH SINGLE MATCH ERROR:",
            str(exc),
        )

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

    print()
    print("========================================")
    print("CRICBET COMPLETE MATCH API")
    print("GAME ID:", game_id)
    print("MARKET ID:", marketId)
    print("========================================")

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        match = proexch_api.get_match(
            game_id
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
                "game_id": game_id,
                "match": match,
                "odds": None,
                "match_result": None,
                "bookmaker_result": None,
                "fancy_results": [],
            }

        complete = (
            proexch_api.get_complete_match_data(
                game_id,
                market_id,
            )
        )

        return {
            "success": True,
            "match": match,
            **complete,
        }

    except Exception as exc:

        print()
        print("========================================")
        print("COMPLETE MATCH ERROR")
        print(str(exc))
        print("========================================")
        print()

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )