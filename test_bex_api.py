from services.bex_api import (
    get_competitions,
    get_events,
    get_market_ids,
    get_market_odds,
    get_market_book,
    get_fancy_bookmaker_odds,
    get_fancy_all_bookmaker_odds_v2,
    get_fancy_all_bookmaker_odds_v3
)


def print_result(name, status, data=None):

    if 200 <= status < 300:

        print(f"✅ {name:<40} {status}")

    else:

        print(f"❌ {name:<40} {status}")

    if data is not None:

        print("   Response:")

        print(
            str(data)[:1000]
        )


def main():

    print()
    print("=" * 70)
    print("                 BEX COMPLETE API TEST")
    print("=" * 70)

    # ==================================================
    # 1. COMPETITIONS
    # ==================================================

    print("\n[1] Competition List")

    try:

        competitions = get_competitions()

        print_result(
            "Competition List",
            200,
            f"{len(competitions)} competitions"
        )

    except Exception as e:

        print_result(
            "Competition List",
            500,
            e
        )

        return

    # ==================================================
    # FIND AN EVENT
    # ==================================================

    selected_event_id = None
    selected_event_name = None

    selected_market_id = None
    selected_market_name = None

    total_events = 0
    total_markets = 0

    print("\nSearching competitions for an event...")

    for item in competitions:

        competition = item.get(
            "competition",
            {}
        )

        competition_id = competition.get("id")
        competition_name = competition.get("name")

        try:

            events = get_events(
                competition_id
            )

        except Exception as e:

            print(
                f"   ⚠ {competition_name}: {e}"
            )

            continue

        total_events += len(events)

        if not events:
            continue

        # First event we find
        if selected_event_id is None:

            event_item = events[0]

            event = event_item.get(
                "event",
                event_item
            )

            selected_event_id = event.get("id")
            selected_event_name = event.get("name")

            print(
                f"\nUsing event:"
                f" {selected_event_name}"
            )

            print(
                f"Event ID: {selected_event_id}"
            )

        # Stop once we have an event
        if selected_event_id:

            break

    # ==================================================
    # 2. EVENT LIST
    # ==================================================

    print("\n[2] Event List")

    if selected_event_id:

        print_result(
            "Event List",
            200,
            f"Found {total_events} events"
        )

    else:

        print_result(
            "Event List",
            404,
            "No events found"
        )

        return

    # ==================================================
    # 3. MARKET IDS
    # ==================================================

    print("\n[3] Market IDs")

    try:

        markets = get_market_ids(
            selected_event_id
        )

        total_markets = len(markets)

        print_result(
            "Market IDs",
            200,
            markets
        )

    except Exception as e:

        print_result(
            "Market IDs",
            500,
            e
        )

        return

    if not markets:

        print(
            "\nNo markets available for this event."
        )

        return

    # ==================================================
    # GET FIRST MARKET ID
    # ==================================================

    market_item = markets[0]

    selected_market_id = market_item.get("marketId")

    selected_market_name = market_item.get(
        "marketName",
        "Unknown market"
    )




    print(
        f"\nUsing market:"
        f" {selected_market_name}"
    )

    print(
        f"Market ID: {selected_market_id}"
    )

    # ==================================================
    # 4. MARKET ODDS BY ID - GET
    # ==================================================

    print("\n[4] Market Odds by ID - GET")

    try:

        odds = get_market_odds(
            selected_event_id,
            selected_market_id
        )

        print_result(
            "Market Odds by ID",
            200,
            odds
        )

    except Exception as e:

        print_result(
            "Market Odds by ID",
            500,
            e
        )

    # ==================================================
    # 5. MARKET ODDS - POST
    # ==================================================

    print("\n[5] Market Odds - POST")

    try:

        market_book = get_market_book(
            selected_market_id
        )

        print_result(
            "Market Odds POST",
            200,
            market_book
        )

    except Exception as e:

        print_result(
            "Market Odds POST",
            500,
            e
        )

    # ==================================================
    # 6. BOOKMAKER FANCY ODDS
    # ==================================================

    print("\n[6] Bookmaker Fancy Odds - GET")

    try:

        fancy = get_fancy_bookmaker_odds(
            selected_event_id
        )

        print_result(
            "Bookmaker Fancy Odds",
            200,
            fancy
        )

    except Exception as e:

        print_result(
            "Bookmaker Fancy Odds",
            500,
            e
        )

    # ==================================================
    # 7. FANCY ALL BOOKMAKER ODDS V2
    # ==================================================

    print("\n[7] Fancy All Bookmaker Odds V2 - GET")

    try:

        fancy_v2 = (
            get_fancy_all_bookmaker_odds_v2(
                selected_event_id
            )
        )

        print_result(
            "Fancy All Bookmaker Odds V2",
            200,
            fancy_v2
        )

    except Exception as e:

        print_result(
            "Fancy All Bookmaker Odds V2",
            500,
            e
        )

    # ==================================================
    # 8. FANCY ALL BOOKMAKER ODDS V3
    # ==================================================

    print("\n[8] Fancy All Bookmaker Odds V3 - GET")

    try:

        fancy_v3 = (
            get_fancy_all_bookmaker_odds_v3(
                selected_event_id
            )
        )

        print_result(
            "Fancy All Bookmaker Odds V3",
            200,
            fancy_v3
        )

    except Exception as e:

        print_result(
            "Fancy All Bookmaker Odds V3",
            500,
            e
        )

    # ==================================================
    # SUMMARY
    # ==================================================

    print()
    print("=" * 70)
    print("                    TEST FINISHED")
    print("=" * 70)

    print(
        f"Events discovered: {total_events}"
    )

    print(
        f"Markets in selected event: {total_markets}"
    )

    print(
        f"Test Event: {selected_event_name}"
    )

    print(
        f"Test Market: {selected_market_name}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()