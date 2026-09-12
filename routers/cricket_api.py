
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services import proexch_api


router = APIRouter(
    tags=["Cricket"],
)

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# AUTH
# ============================================================

def is_logged_in(request: Request) -> bool:
    return request.session.get("user_id") is not None


def unauthorized():
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "error": "Authentication required",
        },
    )


# ============================================================
# GENERIC HELPERS
# ============================================================

def clean(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def first_value(
    data: dict,
    *keys: str,
    default=None,
):
    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return default


def to_number(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value

    try:
        value = str(value).strip()

        if not value:
            return None

        number = float(value)

        if number.is_integer():
            return int(number)

        return number

    except (ValueError, TypeError):
        return None


# ============================================================
# MATCH HELPERS
# ============================================================

def find_match(
    matches: list[dict],
    game_id: str,
) -> dict | None:

    game_id = str(game_id).strip()

    for match in matches:

        if not isinstance(match, dict):
            continue

        current_game_id = first_value(
            match,
            "gameId",
            "game_id",
            "gameID",
        )

        if current_game_id is None:
            continue

        if str(current_game_id).strip() == game_id:
            return match

    return None


def get_match_ids(
    match: dict,
) -> tuple[str | None, str | None]:

    event_id = first_value(
        match,
        "eventId",
        "event_id",
        "eventID",
    )

    market_id = first_value(
        match,
        "marketId",
        "market_id",
        "marketID",
    )

    return (
        clean(event_id),
        clean(market_id),
    )


# ============================================================
# MATCH NORMALIZATION
# ============================================================

def normalize_match(
    match: dict,
) -> dict:

    game_id = first_value(
        match,
        "gameId",
        "game_id",
        "gameID",
    )

    event_id = first_value(
        match,
        "eventId",
        "event_id",
        "eventID",
    )

    market_id = first_value(
        match,
        "marketId",
        "market_id",
        "marketID",
    )

    event_name = first_value(
        match,
        "eventName",
        "event_name",
        "name",
        default="Cricket",
    )

    team1 = first_value(
        match,
        "runnerName1",
        "team1",
        "runner1",
        default="Team 1",
    )

    team2 = first_value(
        match,
        "runnerName2",
        "team2",
        "runner2",
        default="Team 2",
    )

    team3 = first_value(
        match,
        "runnerName3",
        "team3",
        "runner3",
    )

    event_time = first_value(
        match,
        "eventTime",
        "event_time",
        "startTime",
        "start_time",
    )

    in_play = first_value(
        match,
        "inPlay",
        "in_play",
        default=False,
    )

    return {
        "game_id": clean(game_id),
        "event_id": clean(event_id),
        "market_id": clean(market_id),

        "gameId": clean(game_id),
        "eventId": clean(event_id),
        "marketId": clean(market_id),

        "event_name": event_name,
        "eventName": event_name,

        "event_time": event_time,
        "eventTime": event_time,

        "team1": team1,
        "team2": team2,
        "team3": team3,

        "in_play": bool(in_play),
        "inPlay": bool(in_play),

        "tv": first_value(
            match,
            "tv",
            default=False,
        ),

        "raw": match,
    }


# ============================================================
# MATCH ODDS
# ============================================================

def parse_match_odds(
    raw_match_odds,
) -> list[dict]:

    if not isinstance(raw_match_odds, list):
        return []

    markets = []

    for market in raw_match_odds:

        if not isinstance(market, dict):
            continue

        market_id = first_value(
            market,
            "mid",
            "marketId",
            "market_id",
        )

        market_name = first_value(
            market,
            "market",
            "mname",
            "marketName",
            default="Match Odds",
        )

        market_status = first_value(
            market,
            "mstatus",
            "status",
            default="",
        )

        odd_datas = market.get(
            "oddDatas",
            [],
        )

        if not isinstance(odd_datas, list):
            odd_datas = []

        runners = []

        for item in odd_datas:

            if not isinstance(item, dict):
                continue

            selection_id = first_value(
                item,
                "sid",
                "selectionId",
                "selection_id",
                "runnerId",
            )

            runner_name = first_value(
                item,
                "rname",
                "runnerName",
                "selectionName",
                "name",
                default="Unknown",
            )

            back = to_number(
                first_value(
                    item,
                    "b1",
                    "back",
                    "backPrice",
                    "backOdds",
                )
            )

            lay = to_number(
                first_value(
                    item,
                    "l1",
                    "lay",
                    "layPrice",
                    "layOdds",
                )
            )

            back_size = to_number(
                first_value(
                    item,
                    "bs1",
                    "backSize",
                    "backVolume",
                )
            )

            lay_size = to_number(
                first_value(
                    item,
                    "ls1",
                    "laySize",
                    "layVolume",
                )
            )

            runners.append(
                {
                    "id": (
                        str(selection_id)
                        if selection_id is not None
                        else None
                    ),

                    "selection_id": (
                        str(selection_id)
                        if selection_id is not None
                        else None
                    ),

                    "name": str(runner_name),

                    "back": back,
                    "back_size": back_size,

                    "lay": lay,
                    "lay_size": lay_size,

                    "status": item.get(
                        "status",
                        "",
                    ),
                }
            )

        if runners:

            markets.append(
                {
                    "id": (
                        str(market_id)
                        if market_id is not None
                        else None
                    ),

                    "name": str(market_name),

                    "status": market_status,

                    "type": "match_odds",

                    "runners": runners,
                }
            )

    return markets


# ============================================================
# BOOKMAKER ODDS
# ============================================================

def parse_bookmaker_odds(
    raw_bookmaker,
) -> list[dict]:

    if not isinstance(raw_bookmaker, list):
        return []

    markets = []

    for market in raw_bookmaker:

        if not isinstance(market, dict):
            continue

        market_name = first_value(
            market,
            "market",
            "mname",
            "marketName",
            default="Bookmaker",
        )

        odd_datas = market.get(
            "oddDatas",
            [],
        )

        if not isinstance(odd_datas, list):
            odd_datas = []

        runners = []

        for item in odd_datas:

            if not isinstance(item, dict):
                continue

            selection_id = first_value(
                item,
                "sid",
                "selectionId",
                "selection_id",
            )

            name = first_value(
                item,
                "rname",
                "runnerName",
                "selectionName",
                "name",
                default="Unknown",
            )

            runners.append(
                {
                    "id": (
                        str(selection_id)
                        if selection_id is not None
                        else None
                    ),

                    "name": str(name),

                    "back": to_number(
                        first_value(
                            item,
                            "b1",
                            "back",
                            "backPrice",
                        )
                    ),

                    "back_size": to_number(
                        first_value(
                            item,
                            "bs1",
                            "backSize",
                        )
                    ),

                    "lay": to_number(
                        first_value(
                            item,
                            "l1",
                            "lay",
                            "layPrice",
                        )
                    ),

                    "lay_size": to_number(
                        first_value(
                            item,
                            "ls1",
                            "laySize",
                        )
                    ),

                    "status": item.get(
                        "status",
                        "",
                    ),
                }
            )

        if runners:

            markets.append(
                {
                    "id": market.get("mid"),
                    "name": str(market_name),
                    "status": "",
                    "type": "bookmaker",
                    "runners": runners,
                }
            )

    return markets


# ============================================================
# FANCY / SESSION ODDS
# ============================================================

def parse_fancy_odds(
    raw_fancy,
) -> list[dict]:

    if not isinstance(raw_fancy, list):
        return []

    markets = []

    for market in raw_fancy:

        if not isinstance(market, dict):
            continue

        market_id = first_value(
            market,
            "mid",
            "marketId",
            "market_id",
        )

        odd_datas = market.get(
            "oddDatas",
            [],
        )

        if not isinstance(odd_datas, list):
            odd_datas = []

        runners = []

        for item in odd_datas:

            if not isinstance(item, dict):
                continue

            sid = first_value(
                item,
                "sid",
                "selectionId",
                "selection_id",
            )

            name = first_value(
                item,
                "rname",
                "runnerName",
                "selectionName",
                "name",
                default="Session",
            )

            yes = to_number(
                first_value(
                    item,
                    "b1",
                    "yes",
                    "back",
                )
            )

            no = to_number(
                first_value(
                    item,
                    "l1",
                    "no",
                    "lay",
                )
            )

            runners.append(
                {
                    "id": (
                        str(sid)
                        if sid is not None
                        else None
                    ),

                    "name": str(name),

                    "yes": yes,
                    "yes_size": to_number(
                        item.get("bs1")
                    ),

                    "no": no,
                    "no_size": to_number(
                        item.get("ls1")
                    ),

                    "status": item.get(
                        "status",
                        "",
                    ),
                }
            )

        if runners:

            markets.append(
                {
                    "id": (
                        str(market_id)
                        if market_id is not None
                        else None
                    ),

                    "name": "Fancy / Session",

                    "status": "",

                    "type": "fancy",

                    "runners": runners,
                }
            )

    return markets


# ============================================================
# NORMALIZE ODDS
# ============================================================

def normalize_odds(
    raw_odds: dict,
) -> dict:

    if not isinstance(raw_odds, dict):
        raw_odds = {}

    return {
        "match_odds": parse_match_odds(
            raw_odds.get(
                "matchOdds",
                [],
            )
        ),

        "bookmaker_odds": parse_bookmaker_odds(
            raw_odds.get(
                "bookMakerOdds",
                [],
            )
        ),

        "fancy_odds": parse_fancy_odds(
            raw_odds.get(
                "fancyOdds",
                [],
            )
        ),

        "other_market_odds": raw_odds.get(
            "otherMarketOdds",
            [],
        ),

        "raw": raw_odds,
    }


# ============================================================
# BUILD MATCH PAGE DATA
# ============================================================

def build_match_page_data(
    match: dict,
    odds: dict,
) -> dict:

    normalized = normalize_match(
        match
    )

    normalized["status"] = (
        "LIVE"
        if normalized["in_play"]
        else "UPCOMING"
    )

    normalized["league"] = (
        normalized["event_name"]
        or "Cricket"
    )

    normalized["start_time"] = (
        normalized["event_time"]
    )

    normalized["bookmaker"] = "ProExch"

    markets = []

    # --------------------------------------------------------
    # Match Odds
    # --------------------------------------------------------

    for market in odds["match_odds"]:

        outcomes = []

        for runner in market["runners"]:

            outcomes.append(
                {
                    "id": runner["id"],
                    "name": runner["name"],

                    "back": runner["back"],
                    "back_size": runner["back_size"],

                    "lay": runner["lay"],
                    "lay_size": runner["lay_size"],

                    "odds": runner["back"],

                    "status": runner["status"],
                }
            )

        if outcomes:

            markets.append(
                {
                    "id": market["id"],
                    "name": market["name"],
                    "status": market["status"],
                    "type": "match_odds",
                    "outcomes": outcomes,
                }
            )

    # --------------------------------------------------------
    # Bookmaker
    # --------------------------------------------------------

    for market in odds["bookmaker_odds"]:

        outcomes = []

        for runner in market["runners"]:

            outcomes.append(
                {
                    "id": runner["id"],
                    "name": runner["name"],

                    "back": runner["back"],
                    "back_size": runner["back_size"],

                    "lay": runner["lay"],
                    "lay_size": runner["lay_size"],

                    "odds": runner["back"],

                    "status": runner["status"],
                }
            )

        if outcomes:

            markets.append(
                {
                    "id": market["id"],
                    "name": market["name"],
                    "status": "",
                    "type": "bookmaker",
                    "outcomes": outcomes,
                }
            )

    # --------------------------------------------------------
    # Fancy
    # --------------------------------------------------------

    for market in odds["fancy_odds"]:

        outcomes = []

        for runner in market["runners"]:

            outcomes.append(
                {
                    "id": runner["id"],
                    "name": runner["name"],

                    "back": runner["yes"],
                    "back_size": runner["yes_size"],

                    "lay": runner["no"],
                    "lay_size": runner["no_size"],

                    "odds": runner["yes"],

                    "status": runner["status"],
                }
            )

        if outcomes:

            markets.append(
                {
                    "id": market["id"],
                    "name": market["name"],
                    "status": "",
                    "type": "fancy",
                    "outcomes": outcomes,
                }
            )

    normalized["markets"] = markets

    return normalized


# ============================================================
# API - MATCHES
# ============================================================

@router.get("/api/cricket/matches")
async def cricket_matches(
    request: Request,
):

    if not is_logged_in(request):
        return unauthorized()

    try:

        matches = proexch_api.get_matches()

        if not isinstance(matches, list):
            matches = []

        result = [
            normalize_match(match)
            for match in matches
            if isinstance(match, dict)
        ]

        return {
            "success": True,
            "matches": result,
            "count": len(result),
        }

    except Exception as exc:

        print(
            "[CRICKET] matches error:",
            repr(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Unable to load cricket matches",
            },
        )


# ============================================================
# API - ODDS
# ============================================================

@router.get("/api/cricket/odds")
async def cricket_odds(
    request: Request,
    gameId: str,
    eventId: str | None = None,
    marketId: str | None = None,
):

    if not is_logged_in(request):
        return unauthorized()

    game_id = clean(gameId)
    event_id = clean(eventId)
    market_id = clean(marketId)

    if not game_id:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "gameId is required",
            },
        )

    try:

        if not event_id:

            matches = proexch_api.get_matches()

            match = find_match(
                matches,
                game_id,
            )

            if not match:

                return JSONResponse(
                    status_code=404,
                    content={
                        "success": False,
                        "error": "Match not found",
                    },
                )

            event_id, discovered_market_id = (
                get_match_ids(match)
            )

            if not market_id:
                market_id = discovered_market_id

        if not event_id:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "eventId could not be determined",
                },
            )

        raw_odds = proexch_api.get_odds(
            game_id=game_id,
            event_id=event_id,
            market_id=market_id,
        )

        normalized = normalize_odds(
            raw_odds
        )

        return {
            "success": True,

            "game_id": game_id,
            "event_id": event_id,
            "market_id": market_id,

            "match_odds": normalized[
                "match_odds"
            ],

            "bookmaker_odds": normalized[
                "bookmaker_odds"
            ],

            "fancy_odds": normalized[
                "fancy_odds"
            ],

            "other_market_odds": normalized[
                "other_market_odds"
            ],

            "odds": raw_odds,
        }

    except Exception as exc:

        print(
            "[CRICKET] odds error:",
            repr(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Unable to load cricket odds",
            },
        )


# ============================================================
# API - SINGLE MATCH
# ============================================================

@router.get("/api/cricket/match/{game_id}")
async def cricket_match(
    request: Request,
    game_id: str,
):

    if not is_logged_in(request):
        return unauthorized()

    game_id = clean(game_id)

    if not game_id:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Invalid game ID",
            },
        )

    try:

        matches = proexch_api.get_matches()

        match = find_match(
            matches,
            game_id,
        )

        if not match:

            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Match not found",
                },
            )

        event_id, market_id = get_match_ids(
            match
        )

        if not event_id:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "eventId not available",
                },
            )

        raw_odds = proexch_api.get_odds(
            game_id=game_id,
            event_id=event_id,
            market_id=market_id,
        )

        normalized_odds = normalize_odds(
            raw_odds
        )

        return {
            "success": True,

            "game_id": game_id,
            "event_id": event_id,
            "market_id": market_id,

            "match": normalize_match(
                match
            ),

            "match_odds": normalized_odds[
                "match_odds"
            ],

            "bookmaker_odds": normalized_odds[
                "bookmaker_odds"
            ],

            "fancy_odds": normalized_odds[
                "fancy_odds"
            ],

            "other_market_odds": normalized_odds[
                "other_market_odds"
            ],

            "odds": raw_odds,
        }

    except Exception as exc:

        print(
            "[CRICKET] match error:",
            repr(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Unable to load match",
            },
        )


# ============================================================
# HTML - MATCH PAGE
# ============================================================

@router.get("/match/{game_id}")
async def match_page(
    request: Request,
    game_id: str,
):

    if not is_logged_in(request):

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    game_id = clean(game_id)

    if not game_id:

        return templates.TemplateResponse(
            "match.html",
            {
                "request": request,
                "match": None,
                "error": "Invalid match ID.",
            },
        )

    try:

        matches = proexch_api.get_matches()

        match = find_match(
            matches,
            game_id,
        )

        if not match:

            return templates.TemplateResponse(
                "match.html",
                {
                    "request": request,
                    "match": None,
                    "error": "The requested cricket match could not be found.",
                },
            )

        event_id, market_id = get_match_ids(
            match
        )

        if not event_id:

            return templates.TemplateResponse(
                "match.html",
                {
                    "request": request,
                    "match": None,
                    "error": "This match does not have a valid event ID.",
                },
            )

        raw_odds = proexch_api.get_odds(
            game_id=game_id,
            event_id=event_id,
            market_id=market_id,
        )

        normalized_odds = normalize_odds(
            raw_odds
        )

        page_match = build_match_page_data(
            match,
            normalized_odds,
        )

        return templates.TemplateResponse(
            "match.html",
            {
                "request": request,

                "match": page_match,

                "game_id": game_id,
                "event_id": event_id,
                "market_id": market_id,

                "odds": normalized_odds,

                "odds_error": None,
            },
        )

    except Exception as exc:

        print(
            "[CRICKET] match page error:",
            repr(exc),
        )

        return templates.TemplateResponse(
            "match.html",
            {
                "request": request,
                "match": None,
                "error": "Unable to load this cricket match.",
            },
        )

