from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services import proexch_api


router = APIRouter(
    prefix="/api/proexch",
    tags=["ProExch"],
)


# ==========================================================
# HEALTH
# ==========================================================

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


# ==========================================================
# MATCHES
# ==========================================================

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


# ==========================================================
# ODDS
# ==========================================================

@router.get("/odds")
async def odds(
    game_id: str,
    market_id: str,
):

    try:

        data = proexch_api.get_odds(
            game_id,
            market_id,
        )

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


# ==========================================================
# RESULTS
# ==========================================================

@router.get("/results")
async def results(
    market_ids: str,
):

    try:

        ids = [
            x.strip()
            for x in market_ids.split(",")
            if x.strip()
        ]

        data = proexch_api.get_results(ids)

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