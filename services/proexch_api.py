import time
from typing import Any

import requests


# =========================================================
# CONFIGURATION
# =========================================================

BASE_URL = "https://apidata.proexch.in"

REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

# Leave empty because your server IP is whitelisted.
PROXY = ""


# =========================================================
# HTTP SESSION
# =========================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": "CricBet/1.0",
        "Accept": "application/json",
        "Connection": "keep-alive",
    }
)


# =========================================================
# EXCEPTION
# =========================================================

class ProExchError(Exception):
    pass


# =========================================================
# PROXY
# =========================================================

def _get_proxies():
    if not PROXY:
        return None

    return {
        "http": PROXY,
        "https": PROXY,
    }


# =========================================================
# GENERIC REQUEST
# =========================================================

def _request(
    endpoint: str,
    params: dict[str, Any] | None = None,
):
    url = f"{BASE_URL}{endpoint}"

    print()
    print("=" * 60)
    print("PROEXCH REQUEST")
    print("URL:", url)
    print("PARAMS:", params)
    print("PROXY:", PROXY if PROXY else "DIRECT")
    print("=" * 60)

    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):

        try:
            print("ATTEMPT:", attempt)

            response = session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                proxies=_get_proxies(),
            )

            print(
                "PROEXCH HTTP STATUS:",
                response.status_code,
            )

            response.raise_for_status()

            try:
                data = response.json()

            except ValueError as exc:

                raise ProExchError(
                    "ProExch returned invalid JSON."
                ) from exc

            print()
            print("PROEXCH RESPONSE:")
            print(data)
            print()

            return data

        except requests.RequestException as exc:

            last_error = exc

            print(
                "PROEXCH REQUEST ERROR:",
                str(exc),
            )

            if attempt <= MAX_RETRIES:

                delay = attempt

                print(
                    f"Retrying in {delay} second(s)..."
                )

                time.sleep(delay)

        except ProExchError as exc:

            last_error = exc
            break

    raise ProExchError(
        f"ProExch request failed: {last_error}"
    )


# =========================================================
# RESPONSE HELPERS
# =========================================================

def _unwrap_data(data):

    if not isinstance(data, dict):
        return data

    inner = data.get("data")

    if inner is not None:
        return inner

    return data


def _extract_list(data):

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in (
        "data",
        "result",
        "results",
        "matches",
        "odds",
    ):

        value = data.get(key)

        if isinstance(value, list):
            return value

        if isinstance(value, dict):

            nested = value.get("data")

            if isinstance(nested, list):
                return nested

    return []


# =========================================================
# HEALTH CHECK
# =========================================================

def health_check():

    try:

        data = _request(
            "/api/cricket/matches"
        )

        return {
            "status": "ok",
            "base_url": BASE_URL,
            "response": data,
        }

    except Exception as exc:

        raise ProExchError(
            str(exc)
        )


# =========================================================
# MATCHES
# =========================================================

def get_matches():

    data = _request(
        "/api/cricket/matches"
    )

    matches = _extract_list(data)

    print(
        "PROEXCH RAW MATCH COUNT:",
        len(matches),
    )

    return matches


# =========================================================
# EXTRACT MATCH ID
# =========================================================

def _extract_game_id(match):

    if not isinstance(match, dict):
        return None

    value = (
        match.get("gameId")
        or match.get("game_id")
        or match.get("gameID")
    )

    if value is None:
        return None

    value = str(value).strip()

    return value or None


# =========================================================
# EXTRACT EVENT ID
# =========================================================

def _extract_event_id(match):

    if not isinstance(match, dict):
        return None

    value = (
        match.get("eventId")
        or match.get("event_id")
        or match.get("eventID")
    )

    if value is None:
        return None

    value = str(value).strip()

    return value or None


# =========================================================
# EXTRACT MARKET ID
# =========================================================

def _extract_market_id(match):

    if not isinstance(match, dict):
        return None

    value = (
        match.get("marketId")
        or match.get("market_id")
        or match.get("marketID")
    )

    if value is None:
        return None

    value = str(value).strip()

    return value or None


# =========================================================
# FIND MATCH
# =========================================================

def find_match(game_id):

    if game_id is None:
        return None

    game_id = str(game_id).strip()

    if not game_id:
        return None

    matches = get_matches()

    for match in matches:

        if not isinstance(match, dict):
            continue

        current_game_id = _extract_game_id(match)

        if current_game_id == game_id:

            print()
            print("=" * 60)
            print("PROEXCH MATCH FOUND")
            print("gameId:", current_game_id)
            print("eventId:", _extract_event_id(match))
            print("marketId:", _extract_market_id(match))
            print("=" * 60)
            print()

            return match

    print(
        "PROEXCH MATCH NOT FOUND:",
        game_id,
    )

    return None


# =========================================================
# SINGLE MATCH
# =========================================================

def get_match(game_id):

    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    game_id = str(game_id).strip()

    if not game_id:
        raise ProExchError(
            "game_id is empty."
        )

    return find_match(game_id)


# =========================================================
# RESOLVE MATCH IDS
# =========================================================

def resolve_match_ids(
    game_id,
    event_id=None,
    market_id=None,
):
    """
    Resolves eventId and marketId automatically
    from /api/cricket/matches.

    This is important because the View Match page
    may only know the gameId.
    """

    if game_id is None:

        raise ProExchError(
            "game_id is required."
        )

    game_id = str(game_id).strip()

    if not game_id:

        raise ProExchError(
            "game_id is empty."
        )

    # -----------------------------------------------------
    # Clean supplied values
    # -----------------------------------------------------

    if event_id is not None:

        event_id = str(
            event_id
        ).strip()

        if not event_id:
            event_id = None

    if market_id is not None:

        market_id = str(
            market_id
        ).strip()

        if not market_id:
            market_id = None

    # -----------------------------------------------------
    # If both IDs already exist, don't call matches API
    # -----------------------------------------------------

    if event_id:

        print()
        print(
            "PROEXCH IDS ALREADY AVAILABLE"
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

        return (
            game_id,
            event_id,
            market_id,
        )

    # -----------------------------------------------------
    # Resolve from matches API
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("PROEXCH RESOLVING MATCH IDS")
    print("gameId:", game_id)
    print("=" * 60)

    match = find_match(game_id)

    if not match:

        raise ProExchError(
            f"Match not found for game_id={game_id}"
        )

    resolved_event_id = _extract_event_id(
        match
    )

    resolved_market_id = _extract_market_id(
        match
    )

    # Supplied marketId has priority.
    if market_id:
        final_market_id = market_id
    else:
        final_market_id = resolved_market_id

    if not resolved_event_id:

        print(
            "PROEXCH MATCH DATA:",
            match,
        )

        raise ProExchError(
            "ProExch matches API did not return eventId "
            f"for gameId={game_id}."
        )

    print()
    print("=" * 60)
    print("PROEXCH IDS RESOLVED")
    print("gameId:", game_id)
    print("eventId:", resolved_event_id)
    print("marketId:", final_market_id)
    print("=" * 60)
    print()

    return (
        game_id,
        resolved_event_id,
        final_market_id,
    )


# =========================================================
# ODDS
# =========================================================

def get_odds(
    game_id,
    event_id=None,
    market_id=None,
):
    """
    Get ProExch odds.

    eventId is automatically resolved from the
    matches endpoint if it is not supplied.
    """

    # -----------------------------------------------------
    # AUTOMATICALLY RESOLVE IDS
    # -----------------------------------------------------

    (
        game_id,
        event_id,
        market_id,
    ) = resolve_match_ids(
        game_id=game_id,
        event_id=event_id,
        market_id=market_id,
    )

    # -----------------------------------------------------
    # FINAL SAFETY CHECK
    # -----------------------------------------------------

    if not event_id:

        raise ProExchError(
            "Unable to resolve event_id for ProExch odds."
        )

    # -----------------------------------------------------
    # BUILD REQUEST
    # -----------------------------------------------------

    params = {
        "gameId": game_id,
        "eventId": event_id,
    }

    if market_id:

        params["marketId"] = market_id

    print()
    print("=" * 60)
    print("PROEXCH ODDS PARAMETERS")
    print("gameId:", game_id)
    print("eventId:", event_id)
    print("marketId:", market_id)
    print("=" * 60)
    print()

    # -----------------------------------------------------
    # CALL PROEXCH
    # -----------------------------------------------------

    raw = _request(
        "/api/cricket/odds",
        params=params,
    )

    odds = _unwrap_data(raw)

    if not isinstance(odds, dict):
        odds = {}

    # -----------------------------------------------------
    # DEBUG
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("PROEXCH ODDS RECEIVED")
    print(
        "matchOdds:",
        len(
            odds.get(
                "matchOdds",
                [],
            )
            if isinstance(
                odds.get(
                    "matchOdds",
                    [],
                ),
                list,
            )
            else [],
        ),
    )

    print(
        "bookMakerOdds:",
        len(
            odds.get(
                "bookMakerOdds",
                [],
            )
            if isinstance(
                odds.get(
                    "bookMakerOdds",
                    [],
                ),
                list,
            )
            else [],
        ),
    )

    print(
        "fancyOdds:",
        len(
            odds.get(
                "fancyOdds",
                [],
            )
            if isinstance(
                odds.get(
                    "fancyOdds",
                    [],
                ),
                list,
            )
            else [],
        ),
    )

    print("=" * 60)
    print()

    return odds


# =========================================================
# PRICE EXTRACTION
# =========================================================

def _to_float(value):

    if value is None:
        return None

    try:

        number = float(
            str(value).strip()
        )

        if number <= 0:
            return None

        return number

    except (
        TypeError,
        ValueError,
    ):

        return None


def _extract_price(
    data,
    keys,
):

    if not isinstance(data, dict):
        return None

    for key in keys:

        value = data.get(key)

        if value is None:
            continue

        if isinstance(value, dict):

            for nested_key in (
                "price",
                "odds",
                "rate",
                "value",
            ):

                nested_value = value.get(
                    nested_key
                )

                if nested_value is not None:

                    result = _to_float(
                        nested_value
                    )

                    if result is not None:
                        return result

        result = _to_float(value)

        if result is not None:
            return result

    return None


# =========================================================
# PARSE MATCH ODDS
# =========================================================

def parse_match_odds(
    match_odds_raw
):

    if not isinstance(
        match_odds_raw,
        list,
    ):
        return []

    parsed = []

    for market in match_odds_raw:

        if not isinstance(
            market,
            dict,
        ):
            continue

        market_name = (
            market.get("mname")
            or market.get("mName")
            or market.get("marketName")
            or market.get("market")
            or "MATCH ODDS"
        )

        odd_datas = market.get(
            "oddDatas"
        )

        if not isinstance(
            odd_datas,
            list,
        ):
            odd_datas = []

        runners = []

        for odd in odd_datas:

            if not isinstance(
                odd,
                dict,
            ):
                continue

            selection_id = (
                odd.get("sid")
                or odd.get("selectionId")
                or odd.get("selection_id")
            )

            runner_name = (
                odd.get("rname")
                or odd.get("sName")
                or odd.get("runnerName")
                or odd.get("selectionName")
                or odd.get("name")
                or ""
            )

            back = _extract_price(
                odd,
                [
                    "b1",
                    "back",
                    "backPrice",
                    "backOdds",
                    "b1Price",
                ],
            )

            lay = _extract_price(
                odd,
                [
                    "l1",
                    "lay",
                    "layPrice",
                    "layOdds",
                    "l1Price",
                ],
            )

            back_size = _extract_price(
                odd,
                [
                    "bs1",
                    "backSize",
                    "backVolume",
                    "b1Size",
                ],
            )

            lay_size = _extract_price(
                odd,
                [
                    "ls1",
                    "laySize",
                    "layVolume",
                    "l1Size",
                ],
            )

            runners.append(
                {
                    "selection_id": (
                        str(selection_id)
                        if selection_id is not None
                        else ""
                    ),
                    "name": str(
                        runner_name
                    ),
                    "back": back,
                    "lay": lay,
                    "back_size": back_size,
                    "lay_size": lay_size,
                    "raw": odd,
                }
            )

        parsed.append(
            {
                "name": str(
                    market_name
                ),
                "market_name": str(
                    market_name
                ),
                "status": (
                    market.get("mstatus")
                    or market.get("status")
                    or ""
                ),
                "runners": runners,
                "raw": market,
            }
        )

    return parsed


# =========================================================
# PARSE FANCY ODDS
# =========================================================

def parse_fancy_odds(
    fancy_odds_raw
):

    if not isinstance(
        fancy_odds_raw,
        list,
    ):
        return []

    parsed = []

    for market in fancy_odds_raw:

        if not isinstance(
            market,
            dict,
        ):
            continue

        market_name = (
            market.get("mName")
            or market.get("mname")
            or market.get("marketName")
            or market.get("name")
            or "FANCY"
        )

        odd_datas = market.get(
            "oddDatas"
        )

        if not isinstance(
            odd_datas,
            list,
        ):
            odd_datas = []

        rows = []

        for odd in odd_datas:

            if not isinstance(
                odd,
                dict,
            ):
                continue

            sid = (
                odd.get("sid")
                or odd.get("selectionId")
                or odd.get("selection_id")
            )

            name = (
                odd.get("rname")
                or odd.get("sName")
                or odd.get("runnerName")
                or odd.get("selectionName")
                or odd.get("name")
                or ""
            )

            yes = _extract_price(
                odd,
                [
                    "b1",
                    "yes",
                    "yesPrice",
                    "back",
                    "backPrice",
                ],
            )

            no = _extract_price(
                odd,
                [
                    "l1",
                    "no",
                    "noPrice",
                    "lay",
                    "layPrice",
                ],
            )

            yes_size = _extract_price(
                odd,
                [
                    "bs1",
                    "yesSize",
                ],
            )

            no_size = _extract_price(
                odd,
                [
                    "ls1",
                    "noSize",
                ],
            )

            rows.append(
                {
                    "sid": (
                        str(sid)
                        if sid is not None
                        else ""
                    ),
                    "name": str(name),
                    "yes": yes,
                    "no": no,
                    "yes_size": yes_size,
                    "no_size": no_size,
                    "raw": odd,
                }
            )

        parsed.append(
            {
                "name": str(
                    market_name
                ),
                "market_name": str(
                    market_name
                ),
                "odd_datas": rows,
                "status": (
                    market.get("mstatus")
                    or market.get("status")
                    or ""
                ),
                "raw": market,
            }
        )

    return parsed


# =========================================================
# FANCY MARKET IDS
# =========================================================

def get_fancy_market_ids(
    game_id,
    fancy_odds,
):

    if game_id is None:
        return []

    game_id = str(
        game_id
    ).strip()

    if not game_id:
        return []

    if not isinstance(
        fancy_odds,
        list,
    ):
        return []

    market_ids = []

    for market in fancy_odds:

        if not isinstance(
            market,
            dict,
        ):
            continue

        odd_datas = market.get(
            "oddDatas",
            [],
        )

        if not isinstance(
            odd_datas,
            list,
        ):
            continue

        for odd in odd_datas:

            if not isinstance(
                odd,
                dict,
            ):
                continue

            sid = (
                odd.get("sid")
                or odd.get("selectionId")
                or odd.get("selection_id")
            )

            if sid is None:
                continue

            sid = str(sid).strip()

            if not sid:
                continue

            market_id = (
                f"{game_id}_{sid}"
            )

            if market_id not in market_ids:

                market_ids.append(
                    market_id
                )

    return market_ids


# =========================================================
# RESULT
# =========================================================

def get_match_result(
    market_id
):

    if market_id is None:
        raise ProExchError(
            "market_id is required."
        )

    market_id = str(
        market_id
    ).strip()

    if not market_id:
        raise ProExchError(
            "market_id is empty."
        )

    return _request(
        "/api/betfair-result",
        params={
            "marketId": market_id,
            "type": "match_odds",
        },
    )


def get_bookmaker_result(
    game_id
):

    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    game_id = str(
        game_id
    ).strip()

    if not game_id:
        raise ProExchError(
            "game_id is empty."
        )

    return _request(
        "/api/betfair-result",
        params={
            "marketId": game_id,
            "type": "bookmaker",
        },
    )


# =========================================================
# FANCY RESULT
# =========================================================

def get_fancy_result(
    game_id,
    sid,
):

    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    if sid is None:
        raise ProExchError(
            "sid is required."
        )

    market_id = (
        f"{str(game_id).strip()}_"
        f"{str(sid).strip()}"
    )

    return get_fancy_result_by_market_id(
        market_id
    )


def get_fancy_result_by_market_id(
    market_id,
):

    if market_id is None:
        raise ProExchError(
            "market_id is required."
        )

    market_id = str(
        market_id
    ).strip()

    if not market_id:
        raise ProExchError(
            "market_id is empty."
        )

    return _request(
        "/api/betfair-result",
        params={
            "marketId": market_id,
            "type": "new_fancy",
        },
    )


# =========================================================
# ALL FANCY RESULTS
# =========================================================

def get_all_fancy_results(
    odds_data,
    game_id,
):

    if not isinstance(
        odds_data,
        dict,
    ):
        return []

    fancy_odds = odds_data.get(
        "fancyOdds",
        [],
    )

    market_ids = get_fancy_market_ids(
        game_id,
        fancy_odds,
    )

    results = []

    for market_id in market_ids:

        try:

            result = (
                get_fancy_result_by_market_id(
                    market_id
                )
            )

            results.append(
                {
                    "market_id": market_id,
                    "result": result,
                }
            )

        except Exception as exc:

            results.append(
                {
                    "market_id": market_id,
                    "result": None,
                    "error": str(exc),
                }
            )

    return results


# =========================================================
# RESULTS
# =========================================================

def get_results(
    market_ids
):

    if not isinstance(
        market_ids,
        list,
    ):

        market_ids = [
            str(market_ids)
        ]

    results = []

    for market_id in market_ids:

        market_id = str(
            market_id
        ).strip()

        if not market_id:
            continue

        try:

            result = get_match_result(
                market_id
            )

            results.append(
                {
                    "market_id": market_id,
                    "result": result,
                }
            )

        except Exception as exc:

            results.append(
                {
                    "market_id": market_id,
                    "result": None,
                    "error": str(exc),
                }
            )

    return results


# =========================================================
# COMPLETE MATCH DATA
# =========================================================

def get_complete_match_data(
    game_id,
    event_id=None,
    market_id=None,
):
    """
    Complete match data.

    event_id is optional now because get_odds()
    can resolve it automatically.
    """

    (
        game_id,
        event_id,
        market_id,
    ) = resolve_match_ids(
        game_id=game_id,
        event_id=event_id,
        market_id=market_id,
    )

    odds = get_odds(
        game_id=game_id,
        event_id=event_id,
        market_id=market_id,
    )

    # -----------------------------------------------------
    # Parsed MATCH ODDS
    # -----------------------------------------------------

    match_odds = parse_match_odds(
        odds.get(
            "matchOdds",
            [],
        )
    )

    # -----------------------------------------------------
    # Parsed FANCY
    # -----------------------------------------------------

    fancy_odds = parse_fancy_odds(
        odds.get(
            "fancyOdds",
            [],
        )
    )

    # -----------------------------------------------------
    # MATCH RESULT
    # -----------------------------------------------------

    match_result = None

    if market_id:

        try:

            match_result = get_match_result(
                market_id
            )

        except Exception as exc:

            print(
                "MATCH RESULT ERROR:",
                str(exc),
            )

    # -----------------------------------------------------
    # BOOKMAKER RESULT
    # -----------------------------------------------------

    bookmaker_result = None

    try:

        bookmaker_result = (
            get_bookmaker_result(
                game_id
            )
        )

    except Exception as exc:

        print(
            "BOOKMAKER RESULT ERROR:",
            str(exc),
        )

    # -----------------------------------------------------
    # FANCY RESULTS
    # -----------------------------------------------------

    fancy_results = []

    try:

        fancy_results = (
            get_all_fancy_results(
                odds,
                game_id,
            )
        )

    except Exception as exc:

        print(
            "FANCY RESULTS ERROR:",
            str(exc),
        )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {
        "game_id": str(
            game_id
        ),

        "event_id": str(
            event_id
        ),

        "market_id": (
            str(market_id)
            if market_id is not None
            else None
        ),

        "odds": odds,

        "match_odds": match_odds,

        "fancy_odds": fancy_odds,

        "match_result": match_result,

        "bookmaker_result": bookmaker_result,

        "fancy_results": fancy_results,
    }