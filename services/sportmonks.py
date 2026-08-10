import requests

API_KEY = "fufVlI1fq5sw5yEC7YfffeUiyzssnjeWI0ACZEv8n4PZgEWZP7hTfHXrWACt"

BASE_URL = "https://cricket.sportmonks.com/api/v2.0"


def get_teams():
    url = f"{BASE_URL}/teams"

    params = {
        "api_token": API_KEY
    }

    response = requests.get(url, params=params)

    print("Status:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])

    print(response.text)
    return []