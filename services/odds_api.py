from pathlib import Path

import requests
from dotenv import dotenv_values


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

config = dotenv_values(ENV_FILE)

API_KEY = config.get("ODDS_API_KEY")

BASE_URL = "https://api.the-odds-api.com/v4"


def get_cricket_matches():
    sports = [
        "cricket_caribbean_premier_league",
        "cricket_odi",
        "cricket_test_match",
        "cricket_the_hundred",
        "cricket_the_hundred_womens",
    ]

    matches = []

    for sport in sports:

        url = f"{BASE_URL}/sports/{sport}/odds"

        params = {
            "apiKey": API_KEY,
            "regions": "uk",
            "markets": "h2h",
            "oddsFormat": "decimal",
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=15
            )

            print(
                f"{sport}: {response.status_code}"
            )

            if response.status_code == 200:
                data = response.json()
                matches.extend(data)

        except requests.RequestException as e:
            print(f"Error fetching {sport}: {e}")

    return matches