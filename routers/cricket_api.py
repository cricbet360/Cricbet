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

        # =================================================
        # GAME ID
        # =================================================

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

        # =================================================
        # MARKET ID
        # =================================================

        market_id = item.get(
            "marketId"
        )

        market_id = (
            str(market_id).strip()
            if market_id is not None
            else ""
        )

        # =================================================
        # EVENT ID
        # =================================================

        event_id = item.get(
            "eventId"
        )

        event_id = (
            str(event_id).strip()
            if event_id is not None
            else ""
        )

        # =================================================
        # EVENT NAME
        # =================================================

        event_name = str(
            item.get(
                "eventName"
            )
            or "Cricket Match"
        )

        # =================================================
        # EVENT TIME
        # =================================================

        event_time = str(
            item.get(
                "eventTime"
            )
            or ""
        )

        # =================================================
        # IN PLAY
        # =================================================

        in_play = bool(
            item.get(
                "inPlay",
                False,
            )
        )

        # =================================================
        # TV
        # =================================================

        tv = bool(
            item.get(
                "tv",
                False,
            )
        )

        # =================================================
        # TEAMS
        # =================================================

        team1 = str(
            item.get(
                "runnerName1"
            )
            or "Team 1"
        )

        team2 = str(
            item.get(
                "runnerName2"
            )
            or "Team 2"
        )

        team3 = str(
            item.get(
                "runnerName3"
            )
            or "The Draw"
        )

        # =================================================
        # SELECTION IDS
        # =================================================

        selection_id1 = str(
            item.get(
                "selectionId1"
            )
            or ""
        )

        selection_id2 = str(
            item.get(
                "selectionId2"
            )
            or ""
        )

        selection_id3 = str(
            item.get(
                "selectionId3"
            )
            or ""
        )

        # =================================================
        # FINAL MATCH OBJECT
        # =================================================

        result.append(
            {
                "game_id": game_id,

                "market_id": market_id,

                "event_id": event_id,

                "event_name": event_name,

                "event_time": event_time,

                "in_play": in_play,

                "tv": tv,

                "team1": team1,

                "team2": team2,

                "team3": team3,

                "selection_id1": selection_id1,

                "selection_id2": selection_id2,

                "selection_id3": selection_id3,
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
#
# IMPORTANT:
# ProExch requires:
#
# gameId
# eventId
#
# marketId is optional.
#
# Example:
#
# /api/cricket/odds?gameId=123&eventId=456
#
# =========================================================

@router.get("/odds")
async def cricket_odds(
    request: Request,
    gameId: str,
    eventId: str,
    marketId: str = "",
):

    print()
    print("========================================")
    print("CRICBET ODDS API")
    print("GET /api/cricket/odds")
    print("GAME ID:", gameId)
    print("EVENT ID:", eventId)
    print("MARKET ID:", marketId)
    print("========================================")

    # =====================================================
    # AUTH
    # =====================================================

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
                "odds": None,
            },
            status_code=401,
        )

    # =====================================================
    # VALIDATE GAME ID
    # =====================================================

    gameId = str(
        gameId
    ).strip()

    if not gameId:

        return JSONResponse(
            {
                "success": False,
                "error": "gameId is required",
                "odds": None,
            },
            status_code=400,
        )

    # =====================================================
    # VALIDATE EVENT ID
    # =====================================================

    eventId = str(
        eventId
    ).strip()

    if not eventId:

        return JSONResponse(
            {
                "success": False,
                "error": "eventId is required",
                "odds": None,
            },
            status_code=400,
        )

    # =====================================================
    # CLEAN MARKET ID
    # =====================================================

    marketId = (
        str(marketId).strip()
        if marketId
        else ""
    )

    try:

        # =================================================
        # CALL PROEXCH
        #
        # gameId + eventId
        # marketId optional
        # =================================================

        odds = proexch_api.get_odds(
            game_id=gameId,
            event_id=eventId,
            market_id=(
                marketId
                if marketId
                else None
            ),
        )

    except Exception as exc:

        print()
        print(
            "PROEXCH ODDS ERROR:",
            str(exc),
        )
        print()

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "odds": None,
            },
            status_code=502,
        )

    # =====================================================
    # SUCCESS
    # =====================================================

    return {
        "success": True,

        "game_id": gameId,

        "event_id": eventId,

        "market_id": marketId,

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

    # =====================================================
    # AUTH
    # =====================================================

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

    # =====================================================
    # MATCH NOT FOUND
    # =====================================================

    if match is None:

        return JSONResponse(
            {
                "success": False,
                "error": "Match not found",
            },
            status_code=404,
        )

    # =====================================================
    # RETURN MATCH
    # =====================================================

    return {
        "success": True,
        "match": match,
    }


# =========================================================
# COMPLETE MATCH
#
# Example:
#
# /api/cricket/complete/123
#
# The eventId and marketId are automatically taken
# from the ProExch match response.
#
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

    # =====================================================
    # AUTH
    # =====================================================

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
            },
            status_code=401,
        )

    try:

        # =================================================
        # GET MATCH
        # =================================================

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

        # =================================================
        # GET EVENT ID
        #
        # THIS IS REQUIRED BY PROEXCH ODDS API
        # =================================================

        event_id = match.get(
            "eventId"
        )

        if event_id is None:

            return JSONResponse(
                {
                    "success": False,
                    "error": (
                        "eventId not found "
                        "in ProExch match data"
                    ),
                    "match": match,
                },
                status_code=502,
            )

        event_id = str(
            event_id
        ).strip()

        if not event_id:

            return JSONResponse(
                {
                    "success": False,
                    "error": (
                        "eventId is empty "
                        "in ProExch match data"
                    ),
                    "match": match,
                },
                status_code=502,
            )

        # =================================================
        # GET MARKET ID
        # =================================================

        market_id = (
            marketId
            or match.get("marketId")
            or ""
        )

        market_id = (
            str(market_id).strip()
            if market_id
            else ""
        )

        # =================================================
        # DEBUG
        # =================================================

        print()
        print(
            "COMPLETE MATCH IDENTIFIERS"
        )
        print(
            "gameId:",
            game_id,
        )
        print(
            "eventId:",
            event_id,
        )
        print(
            "marketId:",
            market_id,
        )
        print()

        # =================================================
        # GET COMPLETE DATA
        #
        # gameId + eventId
        # marketId optional
        # =================================================

        data = (
            proexch_api.get_complete_match_data(
                game_id=game_id,
                event_id=event_id,
                market_id=(
                    market_id
                    if market_id
                    else None
                ),
            )
        )

        # =================================================
        # RETURN
        # =================================================

        return {
            "success": True,

            "match": match,

            "game_id": str(
                game_id
            ),

            "event_id": event_id,

            "market_id": market_id,

            **data,
        }

    except Exception as exc:

        print()
        print(
            "COMPLETE MATCH ERROR:",
            str(exc),
        )
        print()

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )