import time
from typing import Any

import requests


# =========================================================
# CONFIGURATION
# =========================================================

BASE_URL = "https://apis.professorji.in"

REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

# Optional proxy.
#
# Leave empty if your VPS IP is whitelisted.
#
# Example:
# PROXY = "http://username:password@host:port"
#
PROXY = ""


# =========================================================
# SESSION
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

    proxies = _get_proxies()

    print()
    print("========================================")
    print("PROEXCH REQUEST")
    print("URL:", url)
    print("PARAMS:", params)
    print(
        "PROXY:",
        PROXY if PROXY else "DIRECT"
    )
    print("========================================")

    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):

        try:

            print(
                "ATTEMPT:",
                attempt
            )

            response = session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                proxies=proxies,
            )

            print(
                "PROEXCH HTTP STATUS:",
                response.status_code
            )

            response.raise_for_status()

            try:

                data = response.json()

            except ValueError as exc:

                raise ProExchError(
                    "ProExch returned invalid JSON."
                ) from exc

            return data

        except requests.RequestException as exc:

            last_error = exc

            print(
                "PROEXCH REQUEST ERROR:",
                str(exc)
            )

            if attempt <= MAX_RETRIES:

                delay = attempt

                print(
                    f"Retrying in {delay} second(s)..."
                )

                time.sleep(delay)

            else:

                break

        except ProExchError as exc:

            last_error = exc
            break

    raise ProExchError(
        f"ProExch request failed: {last_error}"
    )


# =========================================================
# EXTRACT LIST FROM API RESPONSE
# =========================================================

def _extract_list(data):

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    # Common envelopes
    candidates = [
        data.get("data"),
        data.get("result"),
        data.get("results"),
        data.get("matches"),
        data.get("odds"),
    ]

    for candidate in candidates:

        if isinstance(candidate, list):
            return candidate

        if isinstance(candidate, dict):

            nested = candidate.get("data")

            if isinstance(nested, list):
                return nested

    return []


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
        len(matches)
    )

    return matches


# =========================================================
# ODDS
#
# IMPORTANT:
# The API supplied by you uses:
#
# /api/cricket/odds?gameId=<gameId>
#
# NOT marketId.
# =========================================================

def get_odds(game_id):

    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    game_id = str(game_id).strip()

    if not game_id:
        raise ProExchError(
            "game_id is empty."
        )

    data = _request(
        "/api/cricket/odds",
        params={
            "gameId": game_id,
        },
    )

    return data


# =========================================================
# MATCH ODDS RESULT
#
# Example:
#
# /api/betfair-result
# ?marketId=1.241309100
# &type=match_odds
# =========================================================

def get_match_result(market_id):

    if market_id is None:
        raise ProExchError(
            "market_id is required."
        )

    market_id = str(market_id).strip()

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


# =========================================================
# BOOKMAKER RESULT
#
# Example:
#
# /api/betfair-result
# ?marketId=34151447
# &type=bookmaker
# =========================================================

def get_bookmaker_result(game_id):

    if game_id is None:
        raise ProExchError(
            "game_id is required."
        )

    game_id = str(game_id).strip()

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
#
# Example:
#
# /api/betfair-result
# ?marketId=34151447_5
# &type=new_fancy
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

    game_id = str(game_id).strip()
    sid = str(sid).strip()

    if not game_id:
        raise ProExchError(
            "game_id is empty."
        )

    if not sid:
        raise ProExchError(
            "sid is empty."
        )

    market_id = f"{game_id}_{sid}"

    return _request(
        "/api/betfair-result",
        params={
            "marketId": market_id,
            "type": "new_fancy",
        },
    )


# =========================================================
# FANCY RESULT BY MARKET ID
# =========================================================

def get_fancy_result_by_market_id(
    market_id,
):

    if market_id is None:
        raise ProExchError(
            "market_id is required."
        )

    market_id = str(market_id).strip()

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
# EXTRACT FANCY SID VALUES
# =========================================================

def get_fancy_market_ids(
    odds_data,
    game_id,
):

    if not isinstance(odds_data, dict):
        return []

    fancy_odds = odds_data.get(
        "fancyOdds",
        []
    )

    if not isinstance(fancy_odds, list):
        return []

    market_ids = []

    for market in fancy_odds:

        if not isinstance(market, dict):
            continue

        odd_datas = market.get(
            "oddDatas",
            []
        )

        if not isinstance(
            odd_datas,
            list
        ):
            continue

        for odd in odd_datas:

            if not isinstance(odd, dict):
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
# ALL FANCY RESULTS
# =========================================================

def get_all_fancy_results(
    odds_data,
    game_id,
):

    market_ids = get_fancy_market_ids(
        odds_data,
        game_id,
    )

    results = []

    for market_id in market_ids:

        try:

            result = get_fancy_result_by_market_id(
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
#
# This performs:
#
# 1. Match odds
# 2. Match result
# 3. Bookmaker result
# 4. Fancy results
# =========================================================

def get_complete_match_data(
    game_id,
    market_id,
):

    print()
    print("========================================")
    print("PROEXCH COMPLETE MATCH DATA")
    print("GAME ID:", game_id)
    print("MARKET ID:", market_id)
    print("========================================")

    # -----------------------------------------------------
    # ODDS
    # -----------------------------------------------------

    odds = get_odds(
        game_id
    )

    # -----------------------------------------------------
    # MATCH RESULT
    # -----------------------------------------------------

    match_result = None

    try:

        match_result = get_match_result(
            market_id
        )

    except Exception as exc:

        print(
            "MATCH RESULT ERROR:",
            str(exc)
        )

    # -----------------------------------------------------
    # BOOKMAKER RESULT
    # -----------------------------------------------------

    bookmaker_result = None

    try:

        bookmaker_result = get_bookmaker_result(
            game_id
        )

    except Exception as exc:

        print(
            "BOOKMAKER RESULT ERROR:",
            str(exc)
        )

    # -----------------------------------------------------
    # FANCY RESULTS
    # -----------------------------------------------------

    fancy_results = []

    try:

        fancy_results = get_all_fancy_results(
            odds,
            game_id,
        )

    except Exception as exc:

        print(
            "FANCY RESULTS ERROR:",
            str(exc)
        )

    return {
        "game_id": str(game_id),
        "market_id": str(market_id),
        "odds": odds,
        "match_result": match_result,
        "bookmaker_result": bookmaker_result,
        "fancy_results": fancy_results,
    }