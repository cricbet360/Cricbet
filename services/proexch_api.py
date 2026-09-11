import os
import time
from typing import Any, Dict, List, Optional

import requests


# ============================================================
# PROEXCH CONFIG
# ============================================================

BASE_URL = "https://apidata.proexch.in"

REQUEST_TIMEOUT = 20
MAX_RETRIES = 2
RETRY_DELAY = 0.5


# ============================================================
# PROXY
#
# Set this in Windows environment:
#
# PROEXCH_PROXY=http://USERNAME:PASSWORD@HOST:PORT
#
# OR:
#
# PROEXCH_PROXY=http://HOST:PORT
#
# Leave empty if ProExch whitelists the machine directly.
# ============================================================

PROEXCH_PROXY = os.getenv(
    "PROEXCH_PROXY",
    ""
).strip()


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "Accept": "application/json",
        "User-Agent": "CrickBet/1.0",
        "Connection": "keep-alive",
    }
)


if PROEXCH_PROXY:

    session.proxies.update(
        {
            "http": PROEXCH_PROXY,
            "https": PROEXCH_PROXY,
        }
    )

    print(
        "PROEXCH PROXY ENABLED:",
        PROEXCH_PROXY
    )

else:

    print(
        "PROEXCH PROXY: NOT CONFIGURED"
    )


# ============================================================
# ERROR
# ============================================================

class ProExchError(Exception):
    pass


# ============================================================
# REQUEST
# ============================================================

def _request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    url = f"{BASE_URL}{endpoint}"

    last_error = None

    for attempt in range(
        MAX_RETRIES + 1
    ):

        try:

            print()
            print(
                "========================================"
            )
            print(
                "PROEXCH REQUEST"
            )
            print(
                "URL:",
                url
            )
            print(
                "PARAMS:",
                params
            )
            print(
                "PROXY:",
                PROEXCH_PROXY
                if PROEXCH_PROXY
                else "DIRECT"
            )
            print(
                "ATTEMPT:",
                attempt + 1
            )
            print(
                "========================================"
            )

            response = session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            print(
                "PROEXCH HTTP STATUS:",
                response.status_code
            )

            if response.status_code == 403:

                print()
                print(
                    "========================================"
                )
                print(
                    "PROEXCH 403 FORBIDDEN"
                )
                print(
                    "The IP reaching ProExch is not "
                    "being accepted."
                )
                print(
                    "========================================"
                )
                print()

                raise ProExchError(
                    "ProExch returned HTTP 403 Forbidden. "
                    "The backend/proxy IP is not whitelisted."
                )

            response.raise_for_status()

            try:

                payload = response.json()

            except ValueError as exc:

                print(
                    "PROEXCH INVALID JSON:"
                )

                print(
                    response.text[:2000]
                )

                raise ProExchError(
                    "ProExch returned invalid JSON"
                ) from exc

            if not isinstance(
                payload,
                dict
            ):

                raise ProExchError(
                    "ProExch returned an unexpected response format"
                )

            status_code = payload.get(
                "statusCode"
            )

            if status_code not in (
                None,
                200,
            ):

                message = payload.get(
                    "message",
                    "ProExch API returned an error"
                )

                raise ProExchError(
                    str(message)
                )

            return payload

        except ProExchError as exc:

            last_error = exc

            print(
                "PROEXCH ERROR:",
                exc
            )

            break

        except requests.Timeout as exc:

            last_error = exc

            print(
                "PROEXCH TIMEOUT:",
                exc
            )

            if attempt >= MAX_RETRIES:
                break

            time.sleep(
                RETRY_DELAY * (
                    attempt + 1
                )
            )

        except requests.ConnectionError as exc:

            last_error = exc

            print(
                "PROEXCH CONNECTION ERROR:",
                exc
            )

            if attempt >= MAX_RETRIES:
                break

            time.sleep(
                RETRY_DELAY * (
                    attempt + 1
                )
            )

        except requests.HTTPError as exc:

            last_error = exc

            print(
                "PROEXCH HTTP ERROR:",
                exc
            )

            status = (
                exc.response.status_code
                if exc.response is not None
                else None
            )

            if status not in (
                429,
                500,
                502,
                503,
                504,
            ):

                break

            if attempt >= MAX_RETRIES:
                break

            time.sleep(
                RETRY_DELAY * (
                    attempt + 1
                )
            )

        except Exception as exc:

            last_error = exc

            print(
                "PROEXCH UNKNOWN ERROR:",
                exc
            )

            break

    raise ProExchError(
        f"ProExch request failed: "
        f"{endpoint}: {last_error}"
    )


# ============================================================
# MATCHES
# ============================================================

def get_matches() -> List[Dict[str, Any]]:

    payload = _request(
        "/api/cricket/matches"
    )

    data = payload.get(
        "data",
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        return []

    matches = data.get(
        "data",
        []
    )

    if not isinstance(
        matches,
        list
    ):
        return []

    print(
        "PROEXCH RAW MATCH COUNT:",
        len(matches)
    )

    return matches


# ============================================================
# SINGLE MATCH
# ============================================================

def get_match(
    game_id: str,
) -> Optional[Dict[str, Any]]:

    if game_id is None:
        return None

    game_id = str(
        game_id
    ).strip()

    if not game_id:
        return None

    matches = get_matches()

    for match in matches:

        if not isinstance(
            match,
            dict
        ):
            continue

        current_game_id = match.get(
            "gameId"
        )

        if current_game_id is None:
            continue

        if (
            str(current_game_id).strip()
            == game_id
        ):

            return match

    return None


# ============================================================
# ODDS
# ============================================================

def get_odds(
    game_id: str,
    market_id: str,
) -> Dict[str, Any]:

    if not game_id:
        raise ValueError(
            "game_id is required"
        )

    if not market_id:
        raise ValueError(
            "market_id is required"
        )

    payload = _request(
        "/api/cricket/odds",
        params={
            "gameId": str(
                game_id
            ),
            "marketId": str(
                market_id
            ),
        },
    )

    data = payload.get(
        "data",
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        return {}

    return data


# ============================================================
# FANCY RESULT
# ============================================================

def get_fancy_result(
    market_ids: List[str],
) -> List[Dict[str, Any]]:

    if not market_ids:
        return []

    cleaned_ids = []

    for market_id in market_ids:

        if market_id is None:
            continue

        market_id = str(
            market_id
        ).strip()

        if not market_id:
            continue

        if "_" not in market_id:
            continue

        cleaned_ids.append(
            market_id
        )

    if not cleaned_ids:
        return []

    payload = _request(
        "/api/betfair-result",
        params={
            "sport": "cricket",
            "type": "new_fancy",
            "marketId": ",".join(
                cleaned_ids
            ),
        },
    )

    data = payload.get(
        "data",
        {}
    )

    if not isinstance(
        data,
        dict
    ):
        return []

    results = data.get(
        "data",
        []
    )

    if not isinstance(
        results,
        list
    ):
        return []

    return results


# ============================================================
# FANCY MARKET IDS
# ============================================================

def get_fancy_market_ids(
    game_id: str,
    fancy_odds: List[Dict[str, Any]],
) -> List[str]:

    result = []

    for market in fancy_odds:

        if not isinstance(
            market,
            dict
        ):
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

            if not isinstance(
                odd,
                dict
            ):
                continue

            sid = odd.get(
                "sid"
            )

            if sid is None:
                continue

            result.append(
                f"{game_id}_{sid}"
            )

    return result


# ============================================================
# MATCH ODDS PARSER
# ============================================================

def parse_match_odds(
    match_odds: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    runners = []

    if not isinstance(
        match_odds,
        list
    ):
        return runners

    for market in match_odds:

        if not isinstance(
            market,
            dict
        ):
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

            if not isinstance(
                odd,
                dict
            ):
                continue

            runners.append(
                {
                    "selection_id": odd.get(
                        "sid"
                    ),
                    "name": odd.get(
                        "rname"
                    ),
                    "status": odd.get(
                        "status"
                    ),
                    "back": [
                        {
                            "price": _to_float(
                                odd.get("b1")
                            ),
                            "size": _to_float(
                                odd.get("bs1")
                            ),
                        },
                        {
                            "price": _to_float(
                                odd.get("b2")
                            ),
                            "size": _to_float(
                                odd.get("bs2")
                            ),
                        },
                        {
                            "price": _to_float(
                                odd.get("b3")
                            ),
                            "size": _to_float(
                                odd.get("bs3")
                            ),
                        },
                    ],
                    "lay": [
                        {
                            "price": _to_float(
                                odd.get("l1")
                            ),
                            "size": _to_float(
                                odd.get("ls1")
                            ),
                        },
                        {
                            "price": _to_float(
                                odd.get("l2")
                            ),
                            "size": _to_float(
                                odd.get("ls2")
                            ),
                        },
                        {
                            "price": _to_float(
                                odd.get("l3")
                            ),
                            "size": _to_float(
                                odd.get("ls3")
                            ),
                        },
                    ],
                }
            )

    return runners


# ============================================================
# FANCY ODDS PARSER
# ============================================================

def parse_fancy_odds(
    fancy_odds: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    result = []

    if not isinstance(
        fancy_odds,
        list
    ):
        return result

    for market in fancy_odds:

        if not isinstance(
            market,
            dict
        ):
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

            if not isinstance(
                odd,
                dict
            ):
                continue

            result.append(
                {
                    "selection_id": odd.get(
                        "sid"
                    ),
                    "name": odd.get(
                        "rname"
                    ),
                    "status": odd.get(
                        "status"
                    ),
                    "remark": odd.get(
                        "remark"
                    ),
                    "min": odd.get(
                        "min"
                    ),
                    "max": odd.get(
                        "max"
                    ),
                    "back": _to_float(
                        odd.get("b1")
                    ),
                    "back_size": _to_float(
                        odd.get("bs1")
                    ),
                    "lay": _to_float(
                        odd.get("l1")
                    ),
                    "lay_size": _to_float(
                        odd.get("ls1")
                    ),
                }
            )

    return result


# ============================================================
# FLOAT CONVERTER
# ============================================================

def _to_float(
    value: Any,
) -> float:

    if value is None:
        return 0.0

    try:
        return float(value)

    except (
        ValueError,
        TypeError,
    ):
        return 0.0