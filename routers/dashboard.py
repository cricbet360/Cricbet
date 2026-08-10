from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User

from services.bex_api import (
    get_competitions,
    get_events,
    get_market_ids,
    get_market_book,
)


router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


# ==========================================================
# RESPONSE HELPERS
# ==========================================================

def unwrap_event(item):
    """
    Handles both:

        {"event": {...}}

    and:

        {...}
    """

    if not isinstance(item, dict):
        return {}

    event = item.get("event")

    if isinstance(event, dict):
        return event

    return item


def unwrap_competition(item):
    """
    Handles both:

        {"competition": {...}}

    and:

        {...}
    """

    if not isinstance(item, dict):
        return {}

    competition = item.get("competition")

    if isinstance(competition, dict):
        return competition

    return item


def get_market_data(book_response, market_id):
    """
    Extract market data from listMarketBook response.

    Expected:

    {
        "status": True,
        "data": [
            {
                "marketId": "...",
                "status": "OPEN",
                "runners": [...]
            }
        ]
    }
    """

    if not isinstance(book_response, dict):
        return None

    data = book_response.get(
        "data",
        []
    )

    if not isinstance(data, list):
        return None

    for market in data:

        if not isinstance(market, dict):
            continue

        returned_market_id = market.get(
            "marketId"
        )

        if str(returned_market_id) == str(market_id):
            return market

    # Some API responses may contain only one market.
    if len(data) == 1 and isinstance(data[0], dict):
        return data[0]

    return None


def get_runner_odds(
    market_data,
    selection_id
):

    if not market_data:
        return {
            "back": None,
            "lay": None,
            "status": "UNKNOWN",
        }

    runners = market_data.get(
        "runners",
        []
    )

    if not isinstance(runners, list):
        return {
            "back": None,
            "lay": None,
            "status": "UNKNOWN",
        }

    for runner in runners:

        if not isinstance(runner, dict):
            continue

        runner_selection_id = runner.get(
            "selectionId"
        )

        if str(
            runner_selection_id
        ) != str(selection_id):

            continue

        exchange = runner.get(
            "ex",
            {}
        )

        if not isinstance(exchange, dict):
            exchange = {}

        back_prices = exchange.get(
            "availableToBack",
            []
        )

        lay_prices = exchange.get(
            "availableToLay",
            []
        )

        if not isinstance(
            back_prices,
            list
        ):
            back_prices = []

        if not isinstance(
            lay_prices,
            list
        ):
            lay_prices = []

        back = None

        lay = None

        if back_prices:

            first_back = back_prices[0]

            if isinstance(
                first_back,
                dict
            ):

                back = first_back.get(
                    "price"
                )

        if lay_prices:

            first_lay = lay_prices[0]

            if isinstance(
                first_lay,
                dict
            ):

                lay = first_lay.get(
                    "price"
                )

        return {
            "back": back,
            "lay": lay,
            "status": runner.get(
                "status",
                "UNKNOWN"
            ),
        }

    return {
        "back": None,
        "lay": None,
        "status": "UNKNOWN",
    }


# ==========================================================
# BEX MATCH BUILDER
# ==========================================================

def build_bex_matches():

    print()
    print("==============================================")
    print("BEX DASHBOARD: START")
    print("==============================================")

    matches = []

    # ------------------------------------------------------
    # COMPETITIONS
    # ------------------------------------------------------

    competitions = get_competitions()

    print(
        f"BEX competitions: {len(competitions)}"
    )

    # ------------------------------------------------------
    # LOOP COMPETITIONS
    # ------------------------------------------------------

    for competition_item in competitions:

        competition = unwrap_competition(
            competition_item
        )

        competition_id = competition.get(
            "id"
        )

        competition_name = competition.get(
            "name",
            "Cricket"
        )

        if not competition_id:
            print(
                "Skipping competition without ID"
            )
            continue

        print(
            f"Competition: "
            f"{competition_name} "
            f"({competition_id})"
        )

        # --------------------------------------------------
        # EVENTS
        # --------------------------------------------------

        try:

            events = get_events(
                competition_id
            )

        except Exception as e:

            print(
                f"EVENT ERROR "
                f"{competition_name}: {e}"
            )

            continue

        print(
            f"  Events found: {len(events)}"
        )

        # --------------------------------------------------
        # LOOP EVENTS
        # --------------------------------------------------

        for event_item in events:

            event = unwrap_event(
                event_item
            )

            event_id = event.get(
                "id"
            )

            event_name = event.get(
                "name",
                "Cricket Match"
            )

            if not event_id:
                print(
                    "  Skipping event without ID"
                )
                continue

            event_name = str(
                event_name
            ).strip()

            print(
                f"  Event: "
                f"{event_name} "
                f"({event_id})"
            )

            # ------------------------------------------------
            # MARKET IDS
            # ------------------------------------------------

            try:

                markets = get_market_ids(
                    event_id
                )

            except Exception as e:

                print(
                    f"    MARKET ERROR: {e}"
                )

                continue

            print(
                f"    Markets found: "
                f"{len(markets)}"
            )

            if not markets:
                continue

            # ------------------------------------------------
            # LOOP MARKETS
            # ------------------------------------------------

            for market in markets:

                if not isinstance(
                    market,
                    dict
                ):
                    continue

                market_id = market.get(
                    "marketId"
                )

                market_name = market.get(
                    "marketName",
                    "Market"
                )

                market_runners = market.get(
                    "runners",
                    []
                )

                if not market_id:
                    continue

                # ------------------------------------------------
                # MARKET BOOK
                # ------------------------------------------------

                try:

                    book_response = get_market_book(
                        [market_id]
                    )

                except Exception as e:

                    print(
                        f"    ODDS ERROR "
                        f"{market_id}: {e}"
                    )

                    continue

                live_market = get_market_data(
                    book_response,
                    market_id
                )

                if not live_market:

                    print(
                        f"    No market data "
                        f"for {market_id}"
                    )

                    continue

                market_status = live_market.get(
                    "status"
                )

                print(
                    f"    Market: "
                    f"{market_name} "
                    f"{market_id} "
                    f"status={market_status}"
                )

                # ------------------------------------------------
                # ONLY SHOW ACTIVE MARKETS
                # ------------------------------------------------

                if market_status not in [
                    "OPEN",
                    "SUSPENDED",
                ]:

                    print(
                        "    Skipping closed market"
                    )

                    continue

                # ------------------------------------------------
                # RUNNERS
                # ------------------------------------------------

                formatted_runners = []

                if not isinstance(
                    market_runners,
                    list
                ):

                    market_runners = []

                for runner in market_runners:

                    if not isinstance(
                        runner,
                        dict
                    ):
                        continue

                    selection_id = runner.get(
                        "selectionId"
                    )

                    runner_name = runner.get(
                        "runnerName",
                        "Unknown"
                    )

                    if not selection_id:
                        continue

                    odds = get_runner_odds(
                        live_market,
                        selection_id
                    )

                    formatted_runners.append({

                        "selection_id":
                            str(selection_id),

                        "name":
                            str(
                                runner_name
                            ).strip(),

                        "back":
                            odds.get(
                                "back"
                            ),

                        "lay":
                            odds.get(
                                "lay"
                            ),

                        "status":
                            odds.get(
                                "status",
                                "UNKNOWN"
                            ),
                    })

                # ------------------------------------------------
                # DON'T ADD EMPTY MARKETS
                # ------------------------------------------------

                if not formatted_runners:

                    print(
                        "    No runners"
                    )

                    continue

                # ------------------------------------------------
                # ADD MATCH
                # ------------------------------------------------

                match = {

                    "event_id":
                        str(event_id),

                    "event_name":
                        event_name,

                    "competition_id":
                        str(competition_id),

                    "competition":
                        str(
                            competition_name
                        ).strip(),

                    "market_id":
                        str(market_id),

                    "market_name":
                        str(
                            market_name
                        ).strip(),

                    "market_status":
                        market_status,

                    "runners":
                        formatted_runners,
                }

                matches.append(
                    match
                )

                print(
                    f"    ADDED MATCH: "
                    f"{event_name} / "
                    f"{market_name}"
                )

    print()
    print(
        f"BEX MATCHES TOTAL: "
        f"{len(matches)}"
    )

    print("==============================================")
    print("BEX DASHBOARD: FINISHED")
    print("==============================================")
    print()

    return matches


# ==========================================================
# DASHBOARD
# ==========================================================

@router.get(
    "/dashboard"
)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    user = db.query(
        User
    ).filter(
        User.id == user_id
    ).first()

    if not user:

        request.session.clear()

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # ------------------------------------------------------
    # GET BEX MATCHES
    # ------------------------------------------------------

    try:

        matches = build_bex_matches()

    except Exception as e:

        print()
        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )

        print(
            f"BEX DASHBOARD FATAL ERROR: {e}"
        )

        print(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        )

        matches = []

    print(
        f"Sending {len(matches)} matches "
        f"to dashboard template"
    )

    # ------------------------------------------------------
    # TEMPLATE
    # ------------------------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "matches": matches,
        },
    )