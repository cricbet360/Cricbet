from pathlib import Path
from dotenv import dotenv_values
import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

config = dotenv_values(ENV_FILE)

API_KEY = config.get("ODDS_API_KEY")

print("Project:", BASE_DIR)
print(".env exists:", ENV_FILE.exists())
print("Key loaded:", bool(API_KEY))
print("Key length:", len(API_KEY or ""))

if not API_KEY:
    raise SystemExit("ERROR: ODDS_API_KEY not found")

url = "https://api.the-odds-api.com/v4/sports"

response = requests.get(
    url,
    params={
        "apiKey": API_KEY
    },
    timeout=15
)

print("Status:", response.status_code)
print(response.text[:5000])