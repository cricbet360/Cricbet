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

def _is_logged_in(request: Request):
    return (
        request.session.get("user_id")
        is not None
    )


# =========================================================
# FIND MATCH BY GAME ID
# =========================================================

def _find_match_by_game_id(
    matches,
    game_id,
):
    """
    Find one ProExch match using gameId.
    """

    if not isinstance(matches, list):
        return None

    target_game_id = str(
        game_id
    ).strip()

    for item in matches:

        if not isinstance(
            item,
            dict,
        ):
            continue

        item_game_id = item.get(
            "gameId"
        )

        if item_game_id is None:
            continue

        if str(
            item_game_id
        ).strip() == target_game_id:

            return item

    return None


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

    # -----------------------------------------------------
    # AUTH
    # -----------------------------------------------------

    if not _is_logged_in(request):

        return JSONResponse(
            {
                "success": False,
                "error": "Not authenticated",
                "matches": [],
            },
            status_code=401,
        )

    # -----------------------------------------------------
    # GET MATCHES FROM PROEXCH
    # -----------------------------------------------------

    try:

        matches = proexch_api.get_matches()

    except Exception as exc:

        print(
            "PROEXCH MATCH ERROR:",
            repr(exc),
        )

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "matches": [],
            },
            status_code=502,
        )

    # -----------------------------------------------------
    # VALIDATE RESPONSE
    # -----------------------------------------------------

    if not isinstance(
        matches,
        list,
    ):

        print(
            "PROEXCH MATCH RESPONSE IS NOT A LIST:",
            type(matches),
        )

        return JSONResponse(
            {
                "success": False,
                "error": "Invalid match response from ProExch",
                "matches": [],
            },
            status_code=502,
        )

    # -----------------------------------------------------
    # BUILD RESPONSE
    # -----------------------------------------------------

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
                "gameId": game_id,

                "market_id": market_id,
                "marketId": market_id,

                "event_id": event_id,
                "eventId": event_id,

                "event_name": event_name,
                "eventName": event_name,

                "event_time": event_time,
                "eventTime": event_time,

                "in_play": in_play,
                "inPlay": in_play,

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
# IMPORTANT
#
# ProExch requires:
#
# gameId
# eventId
#
# The frontend may send:
#
# /api/cricket/odds?gameId=123
#
# In that case we automatically find eventId
# from the match list.
#
# It can also send:
#
# /api/cricket/odds?gameId=123&eventId=456
#
# =========================================================

@router.get("/odds")
async def cricket_odds(
    request: Request,
    gameId: str,
    eventId: str | None = None,
    marketId: str | None = None,
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
    # CLEAN GAME ID
    # =====================================================

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

    # =====================================================
    # CLEAN EVENT ID
    # =====================================================

    event_id = (
        str(eventId).strip()
        if eventId is not None
        else ""
    )

    # =====================================================
    # CLEAN MARKET ID
    # =====================================================

    market_id = (
        str(marketId).strip()
        if marketId is not None
        else ""
    )

    # =====================================================
    # AUTOMATICALLY FIND EVENT ID
    #
    # This fixes requests like:
    #
    # /api/cricket/odds?gameId=-11205357
    #
    # =====================================================

    if not event_id:

        print(
            "EVENT ID NOT PROVIDED."
        )

        print(
            "Looking up gameId:",
            game_id,
            "in ProExch matches..."
        )

        try:

            matches = (
                proexch_api.get_matches()
            )

        except Exception as exc:

            print(
                "PROEXCH MATCH LOOKUP ERROR:",
                repr(exc),
            )

            return JSONResponse(
                {
                    "success": False,
                    "error": (
                        "Could not retrieve match "
                        "information from ProExch."
                    ),
                    "game_id": game_id,
                    "odds": None,
                },
                status_code=502,
            )

        matched = _find_match_by_game_id(
            matches,
            game_id,
        )

        if matched is None:

            print(
                "MATCH NOT FOUND FOR GAME ID:",
                game_id,
            )

            return JSONResponse(
                {
                    "success": False,
                    "error": (
                        "No ProExch match found "
                        f"for gameId {game_id}."
                    ),
                    "game_id": game_id,
                    "odds": None,
                },
                status_code=404,
            )

        # -------------------------------------------------
        # GET EVENT ID
        # -------------------------------------------------

        event_id = matched.get(
            "eventId"
        )

        # Some provider responses may use lowercase
        # or your service may return event_id.

        if event_id is None:

            event_id = matched.get(
                "event_id"
            )

        if event_id is not None:

            event_id = str(
                event_id
            ).strip()

        # -------------------------------------------------
        # GET MARKET ID IF NOT PROVIDED
        # -------------------------------------------------

        if not market_id:

            market_id = matched.get(
                "marketId"
            )

            if market_id is None:

                market_id = matched.get(
                    "market_id"
                )

            if market_id is not None:

                market_id = str(
                    market_id
                ).strip()

        print(
            "MATCH FOUND:",
            matched.get(
                "eventName"
            ),
        )

    # =====================================================
    # EVENT ID STILL MISSING
    # =====================================================

    if not event_id:

        return JSONResponse(
            {
                "success": False,
                "error": (
                    "eventId could not be found "
                    "for this gameId."
                ),
                "game_id": game_id,
                "market_id": market_id,
                "odds": None,
            },
            status_code=400,
        )

    # =====================================================
    # DEBUG IDENTIFIERS
    # =====================================================

    print()
    print(
        "PROEXCH ODDS IDENTIFIERS"
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

    # =====================================================
    # CALL PROEXCH ODDS
    # =====================================================

    try:

        odds = proexch_api.get_odds(
            game_id=game_id,
            event_id=event_id,
            market_id=(
                market_id
                if market_id
                else None
            ),
        )

    except Exception as exc:

        print()
        print(
            "PROEXCH ODDS ERROR:",
            repr(exc),
        )
        print()

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
                "game_id": game_id,
                "event_id": event_id,
                "market_id": market_id,
                "odds": None,
            },
            status_code=502,
        )

    # =====================================================
    # SUCCESS
    # =====================================================

    return {
        "success": True,

        "game_id": game_id,

        "event_id": event_id,

        "market_id": market_id,

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

    # =====================================================
    # GET MATCH
    # =====================================================

    try:

        match = (
            proexch_api.get_match(
                game_id
            )
        )

    except Exception as exc:

        print(
            "PROEXCH SINGLE MATCH ERROR:",
            repr(exc),
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
# Event ID and Market ID are automatically obtained
# from ProExch match data.
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
        # EVENT ID
        # =================================================

        event_id = match.get(
            "eventId"
        )

        if event_id is None:

            event_id = match.get(
                "event_id"
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
        # MARKET ID
        # =================================================

        market_id = (
            marketId
            or match.get("marketId")
            or match.get("market_id")
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
        # COMPLETE DATA
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
            repr(exc),
        )
        print()

        return JSONResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status_code=502,
        )