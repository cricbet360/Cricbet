import os
import time
import random
from typing import Any, Dict, List, Union

import requests
from dotenv import load_dotenv

load_dotenv()


# ==========================================================
# CONFIGURATION
# ==========================================================

API_KEY = os.getenv("BEX_API_KEY")

BASE_URL = "https://trial-api.sportbex.com/api/betfair"

REQUEST_TIMEOUT = 20

MAX_RETRIES = 4

# Do not hammer SportBex.
BASE_RETRY_DELAY = 2.0

# Keep requests serialized at the HTTP wrapper level.
# The dashboard can still batch market-book requests.
MIN_REQUEST_INTERVAL = 0.75


# ==========================================================
# SESSION
# ==========================================================

session = requests.Session()


# ==========================================================
# HEADERS
# ==========================================================

def get_headers() -> Dict[str, str]:
    """
    Headers required by SportBex.
    """

    if not API_KEY:
        raise RuntimeError(
            "BEX_API_KEY is missing from .env"
        )

    return {
        "sportbex-api-key": API_KEY,
        "Accept": "application/json",
        "User-Agent": "Crickbet/1.0",
        "Connection": "keep-alive",
    }


# ==========================================================
# REQUEST THROTTLE
# ==========================================================

_last_request_time = 0.0


def wait_before_request() -> None:
    """
    Prevent a burst of requests against SportBex.
    """

    global _last_request_time

    now = time.monotonic()

    elapsed = now - _last_request_time

    if elapsed < MIN_REQUEST_INTERVAL:

        time.sleep(
            MIN_REQUEST_INTERVAL - elapsed
        )

    _last_request_time = time.monotonic()


# ==========================================================
# RETRY DELAY
# ==========================================================

def get_retry_delay(
    response: requests.Response,
    attempt: int,
) -> float:

    # ------------------------------------------------------
    # Respect Retry-After if SportBex provides it.
    # ------------------------------------------------------

    retry_after = response.headers.get(
        "Retry-After"
    )

    if retry_after:

        try:

            seconds = float(
                retry_after
            )

            return min(
                seconds,
                60.0
            )

        except (
            ValueError,
            TypeError,
        ):
            pass

    # ------------------------------------------------------
    # Exponential backoff + jitter
    #
    # attempt 0 -> ~2 sec
    # attempt 1 -> ~4 sec
    # attempt 2 -> ~8 sec
    # attempt 3 -> ~16 sec
    # ------------------------------------------------------

    delay = (
        BASE_RETRY_DELAY
        * (2 ** attempt)
    )

    jitter = random.uniform(
        0.0,
        0.75
    )

    return min(
        delay + jitter,
        60.0
    )


# ==========================================================
# GENERIC REQUEST
# ==========================================================

def request(
    method: str,
    endpoint: str,
    *,
    data: Any = None,
) -> requests.Response:

    url = f"{BASE_URL}{endpoint}"

    headers = get_headers()

    if method.upper() == "POST":

        headers[
            "Content-Type"
        ] = "application/json"

    last_response = None

    for attempt in range(
        MAX_RETRIES + 1
    ):

        wait_before_request()

        try:

            if method.upper() == "GET":

                response = session.get(
                    url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )

            elif method.upper() == "POST":

                response = session.post(
                    url,
                    headers=headers,
                    json=(
                        data
                        if data is not None
                        else {}
                    ),
                    timeout=REQUEST_TIMEOUT,
                )

            else:

                raise ValueError(
                    f"Unsupported HTTP method: "
                    f"{method}"
                )

            last_response = response

        except requests.RequestException:

            if attempt >= MAX_RETRIES:
                raise

            delay = min(
                BASE_RETRY_DELAY
                * (2 ** attempt),
                60.0,
            )

            delay += random.uniform(
                0,
                0.75
            )

            print(
                f"BEX network error: "
                f"{endpoint} "
                f"→ retrying in "
                f"{delay:.1f}s "
                f"(attempt "
                f"{attempt + 1}/"
                f"{MAX_RETRIES})"
            )

            time.sleep(delay)

            continue

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        if response.status_code < 400:

            return response

        # --------------------------------------------------
        # RATE LIMIT
        # --------------------------------------------------

        if response.status_code == 429:

            if attempt >= MAX_RETRIES:

                print(
                    f"BEX 429: giving up "
                    f"after "
                    f"{MAX_RETRIES + 1} "
                    f"attempts: "
                    f"{endpoint}"
                )

                response.raise_for_status()

            delay = get_retry_delay(
                response,
                attempt,
            )

            print(
                f"BEX 429: "
                f"{endpoint} "
                f"→ retrying in "
                f"{delay:.1f}s "
                f"(attempt "
                f"{attempt + 1}/"
                f"{MAX_RETRIES})"
            )

            time.sleep(delay)

            continue

        # --------------------------------------------------
        # TEMPORARY SERVER ERRORS
        # --------------------------------------------------

        if response.status_code in (
            500,
            502,
            503,
            504,
        ):

            if attempt >= MAX_RETRIES:

                response.raise_for_status()

            delay = min(
                BASE_RETRY_DELAY
                * (2 ** attempt),
                60.0,
            )

            delay += random.uniform(
                0,
                0.75
            )

            print(
                f"BEX {response.status_code}: "
                f"{endpoint} "
                f"→ retrying in "
                f"{delay:.1f}s"
            )

            time.sleep(delay)

            continue

        # --------------------------------------------------
        # OTHER HTTP ERRORS
        # --------------------------------------------------

        response.raise_for_status()

    # Should never normally reach here.
    if last_response is not None:

        last_response.raise_for_status()

    raise RuntimeError(
        f"BEX request failed: {endpoint}"
    )


# ==========================================================
# GENERIC GET
# ==========================================================

def get(
    endpoint: str,
) -> requests.Response:

    return request(
        "GET",
        endpoint,
    )


# ==========================================================
# GENERIC POST
# ==========================================================

def post(
    endpoint: str,
    data: Any = None,
) -> requests.Response:

    return request(
        "POST",
        endpoint,
        data=data,
    )


# ==========================================================
# RESPONSE HELPERS
# ==========================================================

def extract_list(
    response_json: Any,
    possible_keys: List[str] | None = None,
) -> List[Any]:

    if possible_keys is None:
        possible_keys = []

    if isinstance(
        response_json,
        list,
    ):
        return response_json

    if not isinstance(
        response_json,
        dict,
    ):
        return []

    data = response_json.get(
        "data"
    )

    if isinstance(
        data,
        list,
    ):
        return data

    for key in possible_keys:

        value = response_json.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            return value

    return []


# ==========================================================
# 1. COMPETITION LIST
# ==========================================================

def get_competitions() -> List[Dict[str, Any]]:

    response = get(
        "/competition-list/4"
    )

    response.raise_for_status()

    payload = response.json()

    return extract_list(
        payload,
        [
            "competitions",
            "competition",
            "result",
        ],
    )


# ==========================================================
# 2. EVENT LIST
# ==========================================================

def get_events(
    competition_id: Union[str, int],
) -> List[Dict[str, Any]]:

    if not competition_id:
        return []

    response = get(
        f"/event-list/4/{competition_id}"
    )

    response.raise_for_status()

    payload = response.json()

    return extract_list(
        payload,
        [
            "events",
            "event",
            "result",
        ],
    )


# ==========================================================
# 3. MARKET IDS
# ==========================================================

def get_market_ids(
    event_id: Union[str, int],
) -> List[Dict[str, Any]]:

    if not event_id:
        return []

    response = get(
        f"/market-all-list/{event_id}"
    )

    response.raise_for_status()

    payload = response.json()

    return extract_list(
        payload,
        [
            "markets",
            "market",
            "result",
        ],
    )


# ==========================================================
# 4. MARKET ODDS BY ID
# ==========================================================

def get_market_odds(
    event_id: Union[str, int],
    market_id: Union[str, int],
) -> Dict[str, Any]:

    if not event_id:
        raise ValueError(
            "event_id is required"
        )

    if not market_id:
        raise ValueError(
            "market_id is required"
        )

    response = get(
        f"/market-odds/"
        f"{event_id}/"
        f"{market_id}"
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 5. MARKET BOOK
# ==========================================================

def get_market_book(
    market_ids: Union[
        str,
        int,
        List[Union[str, int]],
    ],
) -> Dict[str, Any]:

    if isinstance(
        market_ids,
        (str, int),
    ):

        market_ids = [
            market_ids
        ]

    if not isinstance(
        market_ids,
        list,
    ):

        raise ValueError(
            "market_ids must be a "
            "string, integer, or list"
        )

    cleaned_ids = []

    for market_id in market_ids:

        if market_id is None:
            continue

        market_id = str(
            market_id
        ).strip()

        if not market_id:
            continue

        cleaned_ids.append(
            market_id
        )

    if not cleaned_ids:

        raise ValueError(
            "At least one market ID "
            "is required"
        )

    # SportBex limit.
    cleaned_ids = cleaned_ids[:10]

    payload = {
        "marketIds": cleaned_ids
    }

    response = post(
        "/listMarketBook",
        payload,
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 6. FANCY BOOKMAKER ODDS
# ==========================================================

def get_fancy_bookmaker_odds(
    event_id: Union[str, int],
) -> Dict[str, Any]:

    if not event_id:
        raise ValueError(
            "event_id is required"
        )

    response = get(
        f"/fancy-bookmaker-odds/"
        f"{event_id}"
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 7. FANCY ALL BOOKMAKER ODDS V2
# ==========================================================

def get_fancy_all_bookmaker_odds_v2(
    event_id: Union[str, int],
) -> Dict[str, Any]:

    if not event_id:
        raise ValueError(
            "event_id is required"
        )

    response = get(
        f"/fancy-all-bookmaker-odds-v2/"
        f"{event_id}"
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 8. FANCY ALL BOOKMAKER ODDS V3
# ==========================================================

def get_fancy_all_bookmaker_odds_v3(
    event_id: Union[str, int],
) -> Dict[str, Any]:

    if not event_id:
        raise ValueError(
            "event_id is required"
        )

    response = get(
        f"/fancy-all-bookmaker-odds-v3/"
        f"{event_id}"
    )

    response.raise_for_status()

    return response.json()