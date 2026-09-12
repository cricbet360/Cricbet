from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services import proexch_api


router = APIRouter(
    prefix="/api/proexch",
    tags=["ProExch"],
)


# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
async def health():

    try:

        data = proexch_api.health_check()

        return {
            "ok": True,
            "provider": "ProExch",
            "data": data,
        }

    except proexch_api.ProExchError as exc:

        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "provider": "ProExch",
                "error": str(exc),
            },
        )

    except Exception as exc:

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "provider": "ProExch",
                "error": str(exc),
            },
        )


# =========================================================
# MATCHES
# =========================================================

@router.get("/matches")
async def matches():

    try:

        data = proexch_api.get_matches()

        return {
            "ok": True,
            "provider": "ProExch",
            "data": data,
        }

    except proexch_api.ProExchError as exc:

        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "provider": "ProExch",
                "error": str(exc),
            },
        )

    except Exception as exc:

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "provider": "ProExch",
                "error": str(exc),
            },
        )


# =========================================================
# ODDS
#
# ProExch requires:
# gameId
# eventId
# =========================================================

@router.get("/odds")
async def odds(
    gameId: str,
    eventId: str,
):

    try:

        if not gameId.strip():

            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "provider": "ProExch",
                    "error": "gameId is required",
                },
            )

        if not eventId.strip():

            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "provider": "ProExch",
                    "error": "eventId is required",
                },
            )

        data = proexch_api.get_odds(
            game_id=gameId.strip(),
            event_id=eventId.strip(),
        )

        return {
            "ok": True,
            "provider": "ProExch",
            "gameId": gameId.strip(),
            "eventId": eventId.strip(),
            "data": data,
        }

    except proexch_api.ProExchError as exc:

        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "provider": "ProExch",
                "gameId": gameId,
                "eventId": eventId,
                "error": str(exc),
            },
        )

    except Exception as exc:

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "provider": "ProExch",
                "gameId": gameId,
                "eventId": eventId,
                "error": str(exc),
            },
        )


# =========================================================
# RESULTS
# =========================================================

@router.get("/results")
async def results(
    market_ids: str,
):

    try:

        ids = [
            value.strip()
            for value in market_ids.split(",")
            if value.strip()
        ]

        if not ids:

            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "provider": "ProExch",
                    "error": "At least one market ID is required",
                },
            )

        data = proexch_api.get_results(ids)

        return {
            "ok": True,
            "provider": "ProExch",
            "marketIds": ids,
            "data": data,
        }

    except proexch_api.ProExchError as exc:

        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "provider": "ProExch",
                "error": str(exc),
            },
        )

    except Exception as exc:

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "provider": "ProExch",
                "error": str(exc),
            },
        )