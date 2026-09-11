from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services import proexch_api


router = APIRouter(
    prefix="/api/cricket",
    tags=["Cricket"],
)


@router.get("/matches")
async def cricket_matches(request: Request):

    print()
    print("========================================")
    print("CRICKBET CRICKET MATCH API")
    print("GET /api/cricket/matches")
    print("========================================")

    user_id = request.session.get("user_id")

    print("SESSION USER ID:", user_id)

    if not user_id:
        print("CRICKET API: USER NOT AUTHENTICATED")

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

        market_id = item.get("marketId")
        event_id = item.get("eventId")

        event_name = (
            item.get("eventName")
            or "Cricket Match"
        )

        event_time = (
            item.get("eventTime")
            or ""
        )

        in_play = bool(
            item.get("inPlay", False)
        )

        tv = bool(
            item.get("tv", False)
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
                "event_name": str(event_name),
                "event_time": str(event_time),
                "in_play": in_play,
                "tv": tv,
                "team1": str(team1),
                "team2": str(team2),
                "team3": str(team3),
            }
        )

    print()
    print("PROEXCH MATCHES:", len(result))

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