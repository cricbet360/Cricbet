import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.bet import Bet

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
# SETTINGS
# ==========================================================

# IMPORTANT:
# Do NOT use 12 concurrent requests against SportBex.
# Keep this deliberately low.
MAX_WORKERS = 3

# SportBex market-book endpoint supports arrays.
MARKET_BOOK_BATCH_SIZE = 10

# Delay between retry attempts.
RETRY_DELAYS = (
    1,
    3,
    7,
)

executor = ThreadPoolExecutor(
    max_workers=MAX_WORKERS
)


# ==========================================================
# HELPERS
# ==========================================================

def unwrap_event(item: Any) -> dict:

    if not isinstance(item, dict):
        return {}

    event = item.get("event")

    if isinstance(event, dict):
        return event

    return item


def unwrap_competition(item: Any) -> dict:

    if not isinstance(item, dict):
        return {}

    competition = item.get("competition")

    if isinstance(competition, dict):
        return competition

    return item


def get_market_data(
    book_response: Any,
    market_id: str,
) -> dict | None:

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

    return None


def get_runner_odds(
    market_data: dict | None,
    selection_id: str | int,
) -> dict:

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

        if str(
            runner.get("selectionId")
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
# GET EVENTS FOR ONE COMPETITION
# ==========================================================

def fetch_competition_events(
    competition_item: dict,
) -> list[dict]:

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
        return []

    # Retry event requests as well.
    for attempt, delay in enumerate(
        (0, 2, 5)
    ):

        try:

            events = get_events(
                competition_id
            )

            break

        except Exception as e:

            if attempt >= 2:

                print(
                    f"BEX EVENT ERROR "
                    f"{competition_name}: {e}"
                )

                return []

            print(
                f"BEX EVENT RETRY "
                f"{competition_name}: "
                f"{e}"
            )

            time.sleep(delay)

    result = []

    for event_item in events:

        event = unwrap_event(
            event_item
        )

        event_id = event.get(
            "id"
        )

        if not event_id:
            continue

        result.append({

            "event_id":
                str(event_id),

            "event_name":
                str(
                    event.get(
                        "name",
                        "Cricket Match"
                    )
                ).strip(),

            "competition_id":
                str(competition_id),

            "competition":
                str(
                    competition_name
                ).strip(),

        })

    return result


# ==========================================================
# GET MARKETS FOR ONE EVENT
# ==========================================================

def fetch_event_markets(
    event: dict,
) -> list[dict]:

    event_id = event[
        "event_id"
    ]

    for attempt, delay in enumerate(
        (0, 2, 5)
    ):

        try:

            markets = get_market_ids(
                event_id
            )

            break

        except Exception as e:

            if attempt >= 2:

                print(
                    f"BEX MARKET ERROR "
                    f"{event_id}: {e}"
                )

                return []

            print(
                f"BEX MARKET RETRY "
                f"{event_id}: "
                f"{e}"
            )

            time.sleep(delay)

    result = []

    for market in markets:

        if not isinstance(
            market,
            dict
        ):
            continue

        market_id = market.get(
            "marketId"
        )

        if not market_id:
            continue

        runners = market.get(
            "runners",
            []
        )

        if not isinstance(
            runners,
            list
        ):
            runners = []

        result.append({

            "event_id":
                event_id,

            "event_name":
                event[
                    "event_name"
                ],

            "competition_id":
                event[
                    "competition_id"
                ],

            "competition":
                event[
                    "competition"
                ],

            "market_id":
                str(market_id),

            "market_name":
                str(
                    market.get(
                        "marketName",
                        "Market"
                    )
                ).strip(),

            "runners":
                runners,

        })

    return result


# ==========================================================
# BATCH LIVE MARKET BOOK
# ==========================================================

def fetch_market_book_batch(
    markets: list[dict],
) -> list[dict]:

    if not markets:
        return []

    market_ids = [
        str(
            market["market_id"]
        )
        for market in markets
        if market.get("market_id")
    ]

    if not market_ids:
        return []

    book_response = None

    # ------------------------------------------------------
    # RETRY WHOLE BATCH ON 429 / TEMPORARY FAILURE
    # ------------------------------------------------------

    for attempt, delay in enumerate(
        (0, 2, 5)
    ):

        try:

            book_response = get_market_book(
                market_ids
            )

            break

        except Exception as e:

            if attempt >= 2:

                print(
                    "BEX ODDS BATCH ERROR "
                    f"{market_ids}: {e}"
                )

                return []

            print(
                "BEX ODDS BATCH RETRY "
                f"attempt={attempt + 1}: "
                f"{e}"
            )

            if delay:
                time.sleep(delay)

    if not isinstance(
        book_response,
        dict
    ):
        return []

    data = book_response.get(
        "data",
        []
    )

    if not isinstance(
        data,
        list
    ):
        return []

    # ------------------------------------------------------
    # INDEX LIVE MARKETS BY ID
    # ------------------------------------------------------

    live_by_id = {}

    for live_market in data:

        if not isinstance(
            live_market,
            dict
        ):
            continue

        live_market_id = live_market.get(
            "marketId"
        )

        if live_market_id is None:
            continue

        live_by_id[
            str(live_market_id)
        ] = live_market

    # ------------------------------------------------------
    # FORMAT MARKETS
    # ------------------------------------------------------

    formatted = []

    for market in markets:

        market_id = str(
            market["market_id"]
        )

        live_market = live_by_id.get(
            market_id
        )

        if not live_market:
            continue

        market_status = live_market.get(
            "status"
        )

        if market_status not in (
            "OPEN",
            "SUSPENDED",
        ):
            continue

        formatted_runners = []

        market_runners = market.get(
            "runners",
            []
        )

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

            if not selection_id:
                continue

            runner_name = runner.get(
                "runnerName",
                "Unknown"
            )

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

        if not formatted_runners:
            continue

        formatted.append({

            "event_id":
                market[
                    "event_id"
                ],

            "event_name":
                market[
                    "event_name"
                ],

            "competition_id":
                market[
                    "competition_id"
                ],

            "competition":
                market[
                    "competition"
                ],

            "market_id":
                market[
                    "market_id"
                ],

            "market_name":
                market[
                    "market_name"
                ],

            "market_status":
                market_status,

            "runners":
                formatted_runners,

        })

    return formatted


# ==========================================================
# ASYNC PARALLEL RUNNER
# ==========================================================

async def run_parallel(
    function,
    items,
    *,
    max_workers: int = MAX_WORKERS,
) -> list:

    if not items:
        return []

    loop = asyncio.get_running_loop()

    semaphore = asyncio.Semaphore(
        max_workers
    )

    async def run_one(item):

        async with semaphore:

            return await loop.run_in_executor(
                executor,
                function,
                item
            )

    tasks = [
        run_one(item)
        for item in items
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )

    cleaned = []

    for result in results:

        if isinstance(
            result,
            Exception
        ):

            print(
                f"BEX parallel error: "
                f"{result}"
            )

            continue

        if isinstance(
            result,
            list
        ):

            cleaned.extend(
                result
            )

        elif result is not None:

            cleaned.append(
                result
            )

    return cleaned


# ==========================================================
# BUILD BATCHES
# ==========================================================

def make_batches(
    items: list,
    batch_size: int,
) -> list[list]:

    return [
        items[
            i:i + batch_size
        ]

        for i in range(
            0,
            len(items),
            batch_size
        )
    ]


# ==========================================================
# BUILD BEX MATCHES
# ==========================================================

async def build_bex_matches():

    print()
    print(
        "=============================================="
    )
    print(
        "BEX DASHBOARD: START"
    )
    print(
        "=============================================="
    )

    # ------------------------------------------------------
    # COMPETITIONS
    # ------------------------------------------------------

    try:

        competitions = (
            await asyncio
            .get_running_loop()
            .run_in_executor(
                executor,
                get_competitions
            )
        )

    except Exception as e:

        print(
            f"BEX COMPETITION ERROR: {e}"
        )

        return []

    print(
        f"BEX competitions: "
        f"{len(competitions)}"
    )

    # ------------------------------------------------------
    # EVENTS
    # ------------------------------------------------------

    events = await run_parallel(
        fetch_competition_events,
        competitions,
        max_workers=3
    )

    print(
        f"BEX events discovered: "
        f"{len(events)}"
    )

    if not events:
        return []

    # ------------------------------------------------------
    # MARKETS
    # ------------------------------------------------------

    markets = await run_parallel(
        fetch_event_markets,
        events,
        max_workers=3
    )

    print(
        f"BEX markets discovered: "
        f"{len(markets)}"
    )

    if not markets:
        return []

    # ------------------------------------------------------
    # REMOVE DUPLICATE MARKETS
    # ------------------------------------------------------

    unique_markets = {}

    for market in markets:

        if not isinstance(
            market,
            dict
        ):
            continue

        key = (
            str(
                market.get(
                    "event_id"
                )
            ),
            str(
                market.get(
                    "market_id"
                )
            ),
        )

        unique_markets[key] = market

    markets = list(
        unique_markets.values()
    )

    print(
        f"BEX unique markets: "
        f"{len(markets)}"
    )

    # ------------------------------------------------------
    # BATCH MARKET BOOK REQUESTS
    #
    # Example:
    #
    # 38 markets
    #
    # becomes:
    #
    # batch 1 = 10
    # batch 2 = 10
    # batch 3 = 10
    # batch 4 = 8
    #
    # Instead of 38 POST requests.
    # ------------------------------------------------------

    market_batches = make_batches(
        markets,
        MARKET_BOOK_BATCH_SIZE
    )

    print(
        f"BEX odds batches: "
        f"{len(market_batches)}"
    )

    matches = await run_parallel(
        fetch_market_book_batch,
        market_batches,
        max_workers=2
    )

    # ------------------------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------------------------

    unique = {}

    for match in matches:

        if not isinstance(
            match,
            dict
        ):
            continue

        key = (
            str(
                match.get(
                    "event_id"
                )
            ),
            str(
                match.get(
                    "market_id"
                )
            ),
        )

        unique[key] = match

    matches = list(
        unique.values()
    )

    print()
    print(
        f"BEX LIVE MARKETS: "
        f"{len(matches)}"
    )

    print(
        "=============================================="
    )

    print(
        "BEX DASHBOARD: FINISHED"
    )

    print(
        "=============================================="
    )

    print()

    return matches


# ==========================================================
# FORMAT USER BETS
# ==========================================================

def format_user_bet(
    bet: Bet,
) -> dict:

    created_at = bet.created_at

    if created_at:

        created_at_text = (
            created_at.strftime(
                "%d %b %Y, %I:%M %p"
            )
        )

    else:

        created_at_text = "-"

    return {

        "id":
            bet.id,

        "stake":
            float(
                bet.stake or 0
            ),

        "total_odds":
            float(
                bet.total_odds or 0
            ),

        "potential_win":
            float(
                bet.potential_win or 0
            ),

        "status":
            str(
                bet.status or "pending"
            ).lower(),

        "created_at":
            created_at_text,

    }


# ==========================================================
# DASHBOARD
# ==========================================================

@router.get(
    "/dashboard"
)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # LOGIN CHECK
    # ------------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # ------------------------------------------------------
    # USER
    # ------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        request.session.clear()

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # ------------------------------------------------------
    # BEX MATCHES
    # ------------------------------------------------------

    try:

        matches = (
            await build_bex_matches()
        )

    except Exception as e:

        print(
            f"BEX DASHBOARD ERROR: {e}"
        )

        matches = []

    # ------------------------------------------------------
    # USER BETS
    # ------------------------------------------------------

    try:

        user_bets = (
            db.query(Bet)
            .filter(
                Bet.user_id == user.id
            )
            .order_by(
                Bet.created_at.desc()
            )
            .all()
        )

    except Exception as e:

        print(
            f"USER BETS ERROR: {e}"
        )

        user_bets = []

    formatted_bets = [

        format_user_bet(bet)

        for bet in user_bets

    ]

    # ------------------------------------------------------
    # DASHBOARD LOG
    # ------------------------------------------------------

    print(
        f"Sending "
        f"{len(matches)} "
        f"markets and "
        f"{len(formatted_bets)} "
        f"bets to dashboard"
    )

    # ------------------------------------------------------
    # TEMPLATE
    # ------------------------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={

            "user":
                user,

            "matches":
                matches,

            "bets":
                formatted_bets,

        },
    )