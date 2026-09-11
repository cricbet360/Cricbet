import requests
import json

BASE_URL = "https://apidata.proexch.in"

# From your TEST A response
GAME_ID = "36022943"
MARKET_ID = "1.261925182"

ODDS_URL = f"{BASE_URL}/api/cricket/odds"

params = {
    "gameId": GAME_ID,
    "marketId": MARKET_ID,
}

print("\n" + "=" * 70)
print("TEST D - ODDS API")
print("=" * 70)

print("\nRequest URL:")
print(ODDS_URL)

print("\nParameters:")
print(params)

try:
    response = requests.get(
        ODDS_URL,
        params=params,
        timeout=20
    )

    print("\nHTTP Status:", response.status_code)

    print("\nRaw Response:")
    print(response.text)

    if response.status_code != 200:
        print("\n❌ TEST D FAILED - HTTP error")
        raise SystemExit

    try:
        result = response.json()
    except Exception:
        print("\n❌ Response is not valid JSON")
        raise SystemExit

    print("\nFormatted JSON:")
    print(json.dumps(result, indent=2))

    # ------------------------------------------------------
    # Validate ProExch envelope
    # ------------------------------------------------------

    status_code = result.get("statusCode")

    print("\nProExch statusCode:", status_code)

    if status_code != 200:
        print("\n❌ TEST D FAILED")
        print("HTTP was 200, but ProExch returned an error status.")
        raise SystemExit

    data = result.get("data")

    if not data:
        print("\n⚠️ No odds data returned.")
        raise SystemExit

    print("\n✅ TEST D SUCCESS - Odds data received!")

    # ------------------------------------------------------
    # Show available sections
    # ------------------------------------------------------

    print("\nAvailable sections:")

    if isinstance(data, dict):
        for key in data.keys():
            print("  ✓", key)

    # ------------------------------------------------------
    # Match Odds
    # ------------------------------------------------------

    print("\n" + "-" * 70)
    print("MATCH ODDS")
    print("-" * 70)

    match_odds = data.get("matchOdds")

    if match_odds:
        print(json.dumps(match_odds, indent=2))
    else:
        print("No match odds")

    # ------------------------------------------------------
    # Bookmaker Odds
    # ------------------------------------------------------

    print("\n" + "-" * 70)
    print("BOOKMAKER ODDS")
    print("-" * 70)

    bookmaker_odds = data.get("bookMakerOdds")

    if bookmaker_odds:
        print(json.dumps(bookmaker_odds, indent=2))
    else:
        print("No bookmaker odds")

    # ------------------------------------------------------
    # Fancy / Session Odds
    # ------------------------------------------------------

    print("\n" + "-" * 70)
    print("FANCY / SESSION ODDS")
    print("-" * 70)

    fancy_odds = data.get("fancyOdds")

    if fancy_odds:
        print(json.dumps(fancy_odds, indent=2))
    else:
        print("No fancy odds")

    # ------------------------------------------------------
    # Other Markets
    # ------------------------------------------------------

    print("\n" + "-" * 70)
    print("OTHER MARKET ODDS")
    print("-" * 70)

    other_market_odds = data.get("otherMarketOdds")

    if other_market_odds:
        print(json.dumps(other_market_odds, indent=2))
    else:
        print("No other market odds")

    print("\n" + "=" * 70)
    print("TEST D COMPLETE")
    print("=" * 70)

except requests.RequestException as e:
    print("\n❌ Request failed:")
    print(e)