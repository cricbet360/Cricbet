import os
import requests
from dotenv import load_dotenv


load_dotenv()


API_KEY = os.getenv("BEX_API_KEY")

BASE_URL = "https://trial-api.sportbex.com/api/betfair"


def get_headers():
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
    }


def get(endpoint):
    """
    Generic GET request.
    """

    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=30,
    )

    return response


def post(endpoint, data=None):
    """
    Generic POST request.
    """

    url = f"{BASE_URL}{endpoint}"

    headers = get_headers()

    headers["Content-Type"] = "application/json"

    response = requests.post(
        url,
        headers=headers,
        json=data if data is not None else {},
        timeout=30,
    )

    return response


# ==========================================================
# HELPERS
# ==========================================================

def extract_list(response_json, possible_keys=None):
    """
    SportBex responses are not always returned in exactly
    the same structure.

    This helper safely extracts a list from:
        [...]
        {"data": [...]}
        {"result": [...]}
        {"competitions": [...]}
        etc.
    """

    if possible_keys is None:
        possible_keys = []

    if isinstance(response_json, list):
        return response_json

    if not isinstance(response_json, dict):
        return []

    data = response_json.get("data")

    if isinstance(data, list):
        return data

    for key in possible_keys:

        value = response_json.get(key)

        if isinstance(value, list):
            return value

    return []


# ==========================================================
# 1. COMPETITIONS
# ==========================================================

def get_competitions():

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
# 2. EVENTS
# ==========================================================

def get_events(competition_id):

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

def get_market_ids(event_id):

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
# 4. MARKET ODDS BY ID - GET
# ==========================================================

def get_market_odds(event_id, market_id):

    response = get(
        f"/market-odds/{event_id}/{market_id}"
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 5. MARKET BOOK - POST
# ==========================================================

def get_market_book(market_ids):

    if isinstance(market_ids, str):
        market_ids = [market_ids]

    if not isinstance(market_ids, list):
        raise ValueError(
            "market_ids must be a string or list"
        )

    market_ids = [
        str(x)
        for x in market_ids
        if x
    ]

    if not market_ids:
        raise ValueError(
            "At least one market ID is required"
        )

    if len(market_ids) > 10:
        market_ids = market_ids[:10]

    payload = {
        "marketIds": market_ids
    }

    response = post(
        "/listMarketBook",
        payload
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 6. BOOKMAKER + FANCY ODDS
# ==========================================================

def get_fancy_bookmaker_odds(event_id):

    response = get(
        f"/fancy-bookmaker-odds/{event_id}"
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 7. FANCY ALL BOOKMAKER ODDS V2
# ==========================================================

def get_fancy_all_bookmaker_odds_v2(event_id):

    response = get(
        f"/fancy-all-bookmaker-odds-v2/{event_id}"
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# 8. FANCY ALL BOOKMAKER ODDS V3
# ==========================================================

def get_fancy_all_bookmaker_odds_v3(event_id):

    response = get(
        f"/fancy-all-bookmaker-odds-v3/{event_id}"
    )

    response.raise_for_status()

    return response.json()