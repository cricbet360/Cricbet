from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.wallet import Wallet
from auth.password import hash_password, verify_password

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# -----------------------------
# Register Page
# -----------------------------
@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={}
    )


# -----------------------------
# Register User
# -----------------------------
@router.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    print(f"Registration Attempt -> {username} | {email}")

    # Check username
    existing_user = db.query(User).filter(
        User.username == username
    ).first()

    if existing_user:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "message": "Username already exists"
            }
        )

    # Check email
    existing_email = db.query(User).filter(
        User.email == email
    ).first()

    if existing_email:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "message": "Email already exists"
            }
        )

    # Create User
    new_user = User(
        username=username,
        email=email,
        password=hash_password(password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create Wallet
    wallet = Wallet(
        user_id=new_user.id,
        balance=0.0,
        exposure=0.0
    )

    db.add(wallet)
    db.commit()

    print(f"User Saved Successfully -> ID: {new_user.id}")
    print(f"Wallet Created -> User ID: {new_user.id}")

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# -----------------------------
# Login Page
# -----------------------------
@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


# -----------------------------
# Login User
# -----------------------------
@router.post("/login")
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.username == username
    ).first()

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "message": "Invalid username or password."
            }
        )

    if not verify_password(password, user.password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "message": "Invalid username or password."
            }
        )

    request.session["user_id"] = user.id

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )