from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database.database import Base, engine

from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from models.match import Match
from models.bet import Bet

from auth.session import router as session_router
from auth.routes import router as auth_router

from routers.dashboard import router as dashboard_router
from routers.wallet import router as wallet_router
from routers.api import router as api_router
from routers.bets import router as bets_router

from admin.auth import router as admin_auth_router
from admin.routes import router as admin_router


app = FastAPI(
    title="CrickBet"
)


app.add_middleware(
    SessionMiddleware,
    secret_key="crickbet_super_secret_key_change_this"
)


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


templates = Jinja2Templates(
    directory="templates"
)


@app.get(
    "/",
    response_class=HTMLResponse
)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "user": None
        }
    )


Base.metadata.create_all(
    bind=engine
)


app.include_router(
    auth_router
)

app.include_router(
    session_router
)

app.include_router(
    dashboard_router
)

app.include_router(
    wallet_router
)

app.include_router(
    admin_auth_router
)

app.include_router(
    admin_router
)

app.include_router(
    api_router
)

app.include_router(
    bets_router
)