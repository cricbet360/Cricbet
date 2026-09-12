
import time
from typing import Any

import requests


# =========================================================
# CONFIGURATION
# =========================================================

BASE_URL = "https://apidata.proexch.in"

REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

# Leave empty when your server IP is whitelisted.
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
    print("=" * 50)
    print("PROEXCH REQUEST")
    print("URL:", url)
    print("PARAMS:", params)
    print("PROXY:", PROXY if PROXY else "DIRECT")
    print("=" * 50)

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
        raise ProExchError(str(exc))


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

    matches = get_matches()

    for match in matches:
        if not isinstance(match, dict):
            continue

        current_game_id = (
            match.get("gameId")
            or match.get("game_id")
        )

        if current_game_id is None:
            continue

        if str(current_game_id).strip() == game_id:
            return match

    return None


# =========================================================
# ODDS
# =========================================================

def get_odds(
    game_id,
    event_id=None,
    market_id=None,
):
    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    game_id = str(game_id).strip()

    if not game_id:
        raise ProExchError(
            "game_id is empty."
        )

    if event_id is None:
        raise ProExchError(
            "event_id is required for ProExch odds."
        )

    event_id = str(event_id).strip()

    if not event_id:
        raise ProExchError(
            "event_id is empty."
        )

    params = {
        "gameId": game_id,
        "eventId": event_id,
    }

    if market_id is not None:
        market_id = str(market_id).strip()

        if market_id:
            params["marketId"] = market_id

    print()
    print("=" * 50)
    print("PROEXCH ODDS PARAMETERS")
    print("gameId:", game_id)
    print("eventId:", event_id)
    print(
        "marketId:",
        market_id if market_id else "NOT PROVIDED",
    )
    print("=" * 50)

    raw = _request(
        "/api/cricket/odds",
        params=params,
    )

    odds = _unwrap_data(raw)

    if not isinstance(odds, dict):
        odds = {}

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

def parse_match_odds(match_odds_raw):
    """
    Converts ProExch MATCH_ODDS into:

    [
        {
            "name": "MATCH_ODDS",
            "market_name": "MATCH_ODDS",
            "runners": [
                {
                    "selection_id": "82832996",
                    "name": "Surrey W",
                    "back": 1.62,
                    "lay": 1.63,
                    "back_size": 43.0,
                    "lay_size": 1.0
                }
            ]
        }
    ]
    """

    if not isinstance(match_odds_raw, list):
        return []

    parsed = []

    for market in match_odds_raw:

        if not isinstance(market, dict):
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

        runners_result = []

        for odd in odd_datas:

            if not isinstance(
                odd,
                dict,
            ):
                continue

            # ---------------------------------------------
            # SELECTION ID
            # ---------------------------------------------

            selection_id = (
                odd.get("sid")
                or odd.get("selectionId")
                or odd.get("selection_id")
            )

            # ---------------------------------------------
            # RUNNER NAME
            # IMPORTANT: ProExch uses rname
            # ---------------------------------------------

            runner_name = (
                odd.get("rname")
                or odd.get("sName")
                or odd.get("runnerName")
                or odd.get("selectionName")
                or odd.get("name")
                or ""
            )

            # ---------------------------------------------
            # BACK
            # ProExch uses b1
            # ---------------------------------------------

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

            # ---------------------------------------------
            # LAY
            # ProExch uses l1
            # ---------------------------------------------

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

            # ---------------------------------------------
            # BACK SIZE
            # ---------------------------------------------

            back_size = _extract_price(
                odd,
                [
                    "bs1",
                    "backSize",
                    "backVolume",
                    "b1Size",
                ],
            )

            # ---------------------------------------------
            # LAY SIZE
            # ---------------------------------------------

            lay_size = _extract_price(
                odd,
                [
                    "ls1",
                    "laySize",
                    "layVolume",
                    "l1Size",
                ],
            )

            runners_result.append(
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
                "runners": runners_result,
                "raw": market,
            }
        )

    return parsed


# =========================================================
# PARSE FANCY ODDS
# =========================================================

def parse_fancy_odds(fancy_odds_raw):

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
                    "yes_size": _extract_price(
                        odd,
                        ["bs1"],
                    ),
                    "no_size": _extract_price(
                        odd,
                        ["ls1"],
                    ),
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

    game_id = str(game_id).strip()

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

def get_match_result(market_id):

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


def get_bookmaker_result(game_id):

    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    game_id = str(
        game_id
    ).strip()

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

def get_results(market_ids):

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
    event_id,
    market_id=None,
):
    if not event_id:
        raise ProExchError(
            "event_id is required."
        )

    odds = get_odds(
        game_id=game_id,
        event_id=event_id,
        market_id=market_id,
    )

    # -----------------------------------------------------
    # Parsed data
    # -----------------------------------------------------

    match_odds = parse_match_odds(
        odds.get(
            "matchOdds",
            [],
        )
    )

    fancy_odds = parse_fancy_odds(
        odds.get(
            "fancyOdds",
            [],
        )
    )

    # -----------------------------------------------------
    # Match result
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
    # Bookmaker result
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
    # Fancy results
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

    return {
        "game_id": str(game_id),
        "event_id": str(event_id),
        "market_id": (
            str(market_id)
            if market_id is not None
            else None
        ),

        # Raw provider response
        "odds": odds,

        # Parsed data
        "match_odds": match_odds,
        "fancy_odds": fancy_odds,

        "match_result": match_result,
        "bookmaker_result": bookmaker_result,
        "fancy_results": fancy_results,
    }

