import os
import re
import secrets
import string
import requests

from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Request,
    Form,
    Depends,
)

from fastapi.responses import RedirectResponse

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database.database import get_db

from models.user import User
from models.wallet import Wallet
from models.password_reset_token import PasswordResetToken

from auth.password import (
    hash_password,
    verify_password,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


# =========================================================
# 2FA CONFIGURATION
# =========================================================
#
# Used ONLY for registration phone verification.
#
# Set this in your environment:
#
# TWO_FACTOR_API_KEY=your_key
#
# Do NOT hard-code the API key here.
# =========================================================

TWO_FACTOR_API_KEY = os.getenv(
    "TWO_FACTOR_API_KEY",
    "",
)

OTP_TEMPLATE_NAME = os.getenv(
    "OTP_TEMPLATE_NAME",
    "OTP1",
)


# =========================================================
# PASSWORD RESET CONFIGURATION
# =========================================================

RESET_LINK_EXPIRY_MINUTES = 30


# =========================================================
# HELPERS
# =========================================================

def normalize_phone(phone: str) -> str:
    """
    Keep only digits.

    Supports:
    10-digit Indian numbers
    +91XXXXXXXXXX
    91XXXXXXXXXX
    """

    phone = (phone or "").strip()

    phone = re.sub(
        r"\D",
        "",
        phone,
    )

    if phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]

    return phone


def normalize_referral_code(
    referral_code: str | None,
):
    if not referral_code:
        return None

    referral_code = (
        referral_code
        .strip()
        .upper()
    )

    return referral_code or None


def generate_referral_code(
    db: Session,
) -> str:

    alphabet = (
        string.ascii_uppercase
        + string.digits
    )

    for _ in range(100):

        code = (
            "CB"
            + "".join(
                secrets.choice(alphabet)
                for _ in range(8)
            )
        )

        existing = (
            db.query(User)
            .filter(
                User.referral_code == code
            )
            .first()
        )

        if not existing:
            return code

    raise RuntimeError(
        "Unable to generate unique referral code."
    )


def validate_password(
    password: str,
):

    if len(password) < 8:
        return (
            False,
            "Password must be at least 8 characters.",
        )

    if not re.search(
        r"[A-Z]",
        password,
    ):
        return (
            False,
            "Password must contain at least one uppercase letter.",
        )

    if not re.search(
        r"[a-z]",
        password,
    ):
        return (
            False,
            "Password must contain at least one lowercase letter.",
        )

    if not re.search(
        r"\d",
        password,
    ):
        return (
            False,
            "Password must contain at least one number.",
        )

    if not re.search(
        r"[^A-Za-z0-9]",
        password,
    ):
        return (
            False,
            "Password must contain at least one special character.",
        )

    return True, ""


# =========================================================
# EMAIL VALIDATION
# =========================================================

def is_valid_email(
    email: str,
) -> bool:

    pattern = (
        r"^[A-Za-z0-9._%+-]+"
        r"@"
        r"[A-Za-z0-9.-]+"
        r"\."
        r"[A-Za-z]{2,}$"
    )

    return bool(
        re.match(
            pattern,
            email or "",
        )
    )


# =========================================================
# 2FA SEND OTP
# =========================================================

def send_phone_otp_api(
    phone: str,
):

    if not TWO_FACTOR_API_KEY:

        return {
            "Status": "Error",
            "Details": (
                "2Factor API key is not configured."
            ),
        }

    phone = normalize_phone(phone)

    if len(phone) != 10:

        return {
            "Status": "Error",
            "Details": "Invalid phone number.",
        }

    url = (
        "https://2factor.in/API/V1/"
        f"{TWO_FACTOR_API_KEY}"
        "/SMS/+91"
        f"{phone}"
        "/AUTOGEN2/"
        f"{OTP_TEMPLATE_NAME}"
    )

    try:

        response = requests.get(
            url,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException:

        return {
            "Status": "Error",
            "Details": (
                "Unable to connect to OTP service."
            ),
        }

    except ValueError:

        return {
            "Status": "Error",
            "Details": (
                "Invalid response from OTP service."
            ),
        }


# =========================================================
# 2FA VERIFY OTP
# =========================================================

def verify_phone_otp_api(
    session_id: str,
    otp: str,
):

    if not TWO_FACTOR_API_KEY:

        return {
            "Status": "Error",
            "Details": (
                "2Factor API key is not configured."
            ),
        }

    url = (
        "https://2factor.in/API/V1/"
        f"{TWO_FACTOR_API_KEY}"
        "/SMS/VERIFY/"
        f"{session_id}/"
        f"{otp}"
    )

    try:

        response = requests.get(
            url,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException:

        return {
            "Status": "Error",
            "Details": (
                "Unable to connect to OTP service."
            ),
        }

    except ValueError:

        return {
            "Status": "Error",
            "Details": (
                "Invalid response from OTP service."
            ),
        }


# =========================================================
# REGISTER PAGE
# =========================================================

@router.get("/register")
def register_page(
    request: Request,
):

    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "message": None,
            "username": "",
            "email": "",
            "phone": "",
            "referral_code": "",
        },
    )


# =========================================================
# REGISTER SEND OTP
# =========================================================

@router.post("/register/send-otp")
def register_send_otp(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    referral_code: str = Form(""),
    db: Session = Depends(get_db),
):

    username = username.strip()

    email = email.strip().lower()

    phone = normalize_phone(phone)

    referral_code = normalize_referral_code(
        referral_code
    )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if len(username) < 3:

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "Username must contain at least 3 characters."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    if not is_valid_email(email):

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "Please enter a valid email address."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    if len(phone) != 10:

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "Please enter a valid 10-digit phone number."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    # -----------------------------------------------------
    # DUPLICATE USERNAME
    # -----------------------------------------------------

    existing_username = (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )

    if existing_username:

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "Username already exists."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    # -----------------------------------------------------
    # DUPLICATE EMAIL
    # -----------------------------------------------------

    existing_email = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing_email:

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "Email already registered."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    # -----------------------------------------------------
    # DUPLICATE PHONE
    # -----------------------------------------------------

    existing_phone = (
        db.query(User)
        .filter(
            User.phone == phone
        )
        .first()
    )

    if existing_phone:

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "Phone number already registered."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    # -----------------------------------------------------
    # REFERRAL VALIDATION
    # -----------------------------------------------------

    if referral_code:

        referrer = (
            db.query(User)
            .filter(
                User.referral_code
                == referral_code,
                User.status
                == "Active",
            )
            .first()
        )

        if not referrer:

            return templates.TemplateResponse(
                "register.html",
                {
                    "request": request,
                    "message": (
                        "Invalid referral code."
                    ),
                    "username": username,
                    "email": email,
                    "phone": phone,
                    "referral_code": referral_code,
                },
            )

    # -----------------------------------------------------
    # SEND OTP
    # -----------------------------------------------------

    result = send_phone_otp_api(
        phone
    )

    if result.get("Status") != "Success":

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    result.get("Details")
                    or "Unable to send OTP."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    session_id = result.get(
        "Details"
    )

    if not session_id:

        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "message": (
                    "OTP service did not return a session ID."
                ),
                "username": username,
                "email": email,
                "phone": phone,
                "referral_code": (
                    referral_code or ""
                ),
            },
        )

    # -----------------------------------------------------
    # SAVE REGISTRATION SESSION
    # -----------------------------------------------------

    request.session[
        "registration_username"
    ] = username

    request.session[
        "registration_email"
    ] = email

    request.session[
        "registration_phone"
    ] = phone

    request.session[
        "registration_referral_code"
    ] = referral_code

    request.session[
        "registration_otp_session_id"
    ] = session_id

    request.session[
        "registration_otp_expiry"
    ] = (
        datetime.utcnow()
        + timedelta(minutes=10)
    ).isoformat()

    return RedirectResponse(
        "/register/verify-otp",
        status_code=303,
    )


# =========================================================
# REGISTER VERIFY OTP PAGE
# =========================================================

@router.get("/register/verify-otp")
def register_verify_otp_page(
    request: Request,
):

    return templates.TemplateResponse(
        "verify-otp.html",
        {
            "request": request,
            "phone": request.session.get(
                "registration_phone"
            ),
        },
    )


# =========================================================
# REGISTER VERIFY OTP
# =========================================================

@router.post("/register/verify-otp")
def register_verify_otp(
    request: Request,
    otp: str = Form(...),
):

    session_id = request.session.get(
        "registration_otp_session_id"
    )

    expiry = request.session.get(
        "registration_otp_expiry"
    )

    phone = request.session.get(
        "registration_phone"
    )

    if not session_id or not expiry:

        return templates.TemplateResponse(
            "verify-otp.html",
            {
                "request": request,
                "phone": phone,
                "message": (
                    "OTP session expired. Please register again."
                ),
            },
        )

    try:

        expiry_dt = datetime.fromisoformat(
            expiry
        )

    except (ValueError, TypeError):

        return templates.TemplateResponse(
            "verify-otp.html",
            {
                "request": request,
                "phone": phone,
                "message": (
                    "Invalid OTP session."
                ),
            },
        )

    if datetime.utcnow() > expiry_dt:

        request.session.pop(
            "registration_otp_session_id",
            None,
        )

        request.session.pop(
            "registration_otp_expiry",
            None,
        )

        return templates.TemplateResponse(
            "verify-otp.html",
            {
                "request": request,
                "phone": phone,
                "message": (
                    "OTP expired. Please register again."
                ),
            },
        )

    result = verify_phone_otp_api(
        session_id,
        otp.strip(),
    )

    if result.get("Status") != "Success":

        return templates.TemplateResponse(
            "verify-otp.html",
            {
                "request": request,
                "phone": phone,
                "message": (
                    result.get("Details")
                    or "Invalid OTP."
                ),
            },
        )

    # -----------------------------------------------------
    # OTP VERIFIED
    # -----------------------------------------------------

    request.session[
        "registration_phone_verified"
    ] = True

    request.session.pop(
        "registration_otp_session_id",
        None,
    )

    request.session.pop(
        "registration_otp_expiry",
        None,
    )

    return RedirectResponse(
        "/register/disclaimer",
        status_code=303,
    )


# =========================================================
# DISCLAIMER PAGE
# =========================================================

@router.get("/register/disclaimer")
def register_disclaimer_page(
    request: Request,
):

    if not request.session.get(
        "registration_phone_verified"
    ):

        return RedirectResponse(
            "/register",
            status_code=303,
        )

    return templates.TemplateResponse(
        "disclaimer.html",
        {
            "request": request,
        },
    )


# =========================================================
# ACCEPT DISCLAIMER
# =========================================================

@router.post("/register/disclaimer")
def register_disclaimer(
    request: Request,
):

    if not request.session.get(
        "registration_phone_verified"
    ):

        return RedirectResponse(
            "/register",
            status_code=303,
        )

    request.session[
        "registration_disclaimer_accepted"
    ] = True

    return RedirectResponse(
        "/register/create-password",
        status_code=303,
    )


# =========================================================
# CREATE PASSWORD PAGE
# =========================================================

@router.get("/register/create-password")
def create_password_page(
    request: Request,
):

    if not request.session.get(
        "registration_phone_verified"
    ):

        return RedirectResponse(
            "/register",
            status_code=303,
        )

    if not request.session.get(
        "registration_disclaimer_accepted"
    ):

        return RedirectResponse(
            "/register/disclaimer",
            status_code=303,
        )

    return templates.TemplateResponse(
        "create-password.html",
        {
            "request": request,
        },
    )


# =========================================================
# CREATE PASSWORD / CREATE USER
# =========================================================

@router.post("/register/create-password")
def create_password(
    request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):

    if not request.session.get(
        "registration_phone_verified"
    ):

        return RedirectResponse(
            "/register",
            status_code=303,
        )

    if not request.session.get(
        "registration_disclaimer_accepted"
    ):

        return RedirectResponse(
            "/register/disclaimer",
            status_code=303,
        )

    username = request.session.get(
        "registration_username"
    )

    email = request.session.get(
        "registration_email"
    )

    phone = normalize_phone(
        request.session.get(
            "registration_phone"
        )
    )

    referral_code = normalize_referral_code(
        request.session.get(
            "registration_referral_code"
        )
    )

    if not username or not email or not phone:

        return RedirectResponse(
            "/register",
            status_code=303,
        )

    # -----------------------------------------------------
    # PASSWORD VALIDATION
    # -----------------------------------------------------

    if password != confirm_password:

        return templates.TemplateResponse(
            "create-password.html",
            {
                "request": request,
                "message": (
                    "Passwords do not match."
                ),
            },
        )

    valid, message = validate_password(
        password
    )

    if not valid:

        return templates.TemplateResponse(
            "create-password.html",
            {
                "request": request,
                "message": message,
            },
        )

    # -----------------------------------------------------
    # REFERRER REVALIDATION
    # -----------------------------------------------------

    referred_by_user_id = None

    if referral_code:

        referrer = (
            db.query(User)
            .filter(
                User.referral_code
                == referral_code,
                User.status
                == "Active",
            )
            .first()
        )

        if not referrer:

            return templates.TemplateResponse(
                "create-password.html",
                {
                    "request": request,
                    "message": (
                        "Referral code is no longer valid."
                    ),
                },
            )

        # Prevent self-referral.
        if (
            referrer.phone == phone
            or referrer.email == email
            or referrer.username == username
        ):

            return templates.TemplateResponse(
                "create-password.html",
                {
                    "request": request,
                    "message": (
                        "You cannot use your own referral code."
                    ),
                },
            )

        referred_by_user_id = (
            referrer.id
        )

    # -----------------------------------------------------
    # FINAL DUPLICATE CHECK
    # -----------------------------------------------------

    existing = (
        db.query(User)
        .filter(
            (
                User.username
                == username
            )
            |
            (
                User.email
                == email
            )
            |
            (
                User.phone
                == phone
            )
        )
        .first()
    )

    if existing:

        return templates.TemplateResponse(
            "create-password.html",
            {
                "request": request,
                "message": (
                    "User details are already registered."
                ),
            },
        )

    # -----------------------------------------------------
    # GENERATE REFERRAL CODE
    # -----------------------------------------------------

    referral_generated_code = (
        generate_referral_code(db)
    )

    # -----------------------------------------------------
    # CREATE USER
    # -----------------------------------------------------

    user = User(
        username=username,
        email=email,
        phone=phone,
        password=hash_password(
            password
        ),
        status="Active",
        referral_code=(
            referral_generated_code
        ),
        referred_by_user_id=(
            referred_by_user_id
        ),
        first_deposit_completed=False,
        referral_bonus_paid=False,
    )

    db.add(user)

    try:

        db.flush()

        # -------------------------------------------------
        # CREATE WALLET
        # -------------------------------------------------

        wallet = Wallet(
            user_id=user.id,
            balance=0,
            exposure=0,
        )

        db.add(wallet)

        db.commit()

    except Exception:

        db.rollback()

        return templates.TemplateResponse(
            "create-password.html",
            {
                "request": request,
                "message": (
                    "Unable to create account. Please try again."
                ),
            },
        )

    # -----------------------------------------------------
    # CLEAR REGISTRATION SESSION
    # -----------------------------------------------------

    for key in [

        "registration_username",
        "registration_email",
        "registration_phone",
        "registration_referral_code",
        "registration_otp_session_id",
        "registration_otp_expiry",
        "registration_phone_verified",
        "registration_disclaimer_accepted",

    ]:

        request.session.pop(
            key,
            None,
        )

    return RedirectResponse(
        "/login?registered=1",
        status_code=303,
    )


# =========================================================
# LOGIN PAGE
# =========================================================

@router.get("/login")
def login_page(
    request: Request,
):

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
        },
    )


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
def login(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    phone = normalize_phone(
        phone
    )

    user = (
        db.query(User)
        .filter(
            User.phone == phone
        )
        .first()
    )

    if not user:

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "message": (
                    "Invalid phone number or password."
                ),
            },
        )

    if user.status != "Active":

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "message": (
                    "Your account is not active."
                ),
            },
        )

    if not verify_password(
        password,
        user.password,
    ):

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "message": (
                    "Invalid phone number or password."
                ),
            },
        )

    # -----------------------------------------------------
    # LOGIN SESSION
    # -----------------------------------------------------

    request.session.clear()

    request.session[
        "user_id"
    ] = user.id

    return RedirectResponse(
        "/dashboard",
        status_code=303,
    )


# =========================================================
# FORGOT PASSWORD PAGE
# =========================================================
#
# IMPORTANT:
#
# There is NO OTP here.
#
# The admin generates a secure reset link.
# =========================================================

@router.get("/forgot-password")
def forgot_password_page(
    request: Request,
):

    return templates.TemplateResponse(
        "forgot-password.html",
        {
            "request": request,
        },
    )


# =========================================================
# FORGOT PASSWORD POST
# =========================================================

@router.post("/forgot-password")
def forgot_password(
    request: Request,
):

    return templates.TemplateResponse(
        "forgot-password.html",
        {
            "request": request,
            "message": (
                "Please contact CrickBet admin/support "
                "to receive a password reset link."
            ),
        },
    )


# =========================================================
# ADMIN-GENERATED RESET PASSWORD PAGE
# =========================================================

@router.get(
    "/reset-password/admin/{token}"
)
def admin_reset_password_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):

    token = token.strip()

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token
            == token
        )
        .first()
    )

    # -----------------------------------------------------
    # TOKEN NOT FOUND
    # -----------------------------------------------------

    if not reset_token:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "Invalid password reset link."
                ),
            },
        )

    # -----------------------------------------------------
    # TOKEN USED
    # -----------------------------------------------------

    if reset_token.used_at is not None:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "This password reset link "
                    "has already been used."
                ),
            },
        )

    # -----------------------------------------------------
    # TOKEN EXPIRED
    # -----------------------------------------------------

    if datetime.utcnow() > reset_token.expires_at:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "This password reset link has expired. "
                    "Please contact admin for a new link."
                ),
            },
        )

    # -----------------------------------------------------
    # VALID TOKEN
    # -----------------------------------------------------

    return templates.TemplateResponse(
        "reset-password-admin.html",
        {
            "request": request,
            "valid": True,
            "success": False,
            "token": token,
            "message": None,
        },
    )


# =========================================================
# ADMIN-GENERATED RESET PASSWORD
# =========================================================

@router.post(
    "/reset-password/admin/{token}"
)
def admin_reset_password(
    request: Request,
    token: str,
    user_id: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):

    token = token.strip()

    user_id = user_id.strip()

    phone = phone.strip()

    # -----------------------------------------------------
    # FIND TOKEN
    # -----------------------------------------------------

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token
            == token
        )
        .first()
    )

    if not reset_token:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "Invalid password reset link."
                ),
            },
        )

    # -----------------------------------------------------
    # USED CHECK
    # -----------------------------------------------------

    if reset_token.used_at is not None:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "This reset link has already been used."
                ),
            },
        )

    # -----------------------------------------------------
    # EXPIRY CHECK
    # -----------------------------------------------------

    if datetime.utcnow() > reset_token.expires_at:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "This reset link has expired. "
                    "Please contact admin for a new link."
                ),
            },
        )

    # -----------------------------------------------------
    # VALIDATE USER ID
    # -----------------------------------------------------

    try:

        entered_user_id = int(
            user_id
        )

    except (
        ValueError,
        TypeError,
    ):

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": True,
                "success": False,
                "token": token,
                "message": (
                    "Please enter a valid User ID."
                ),
                "user_id": user_id,
                "phone": phone,
            },
        )

    # -----------------------------------------------------
    # TOKEN MUST BELONG TO THIS USER
    # -----------------------------------------------------

    if (
        entered_user_id
        != reset_token.user_id
    ):

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": True,
                "success": False,
                "token": token,
                "message": (
                    "User ID does not match this reset link."
                ),
                "user_id": user_id,
                "phone": phone,
            },
        )

    # -----------------------------------------------------
    # GET USER
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id
            == reset_token.user_id
        )
        .first()
    )

    if not user:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": False,
                "success": False,
                "message": (
                    "User account could not be found."
                ),
            },
        )

    # -----------------------------------------------------
    # VERIFY PHONE
    # -----------------------------------------------------

    entered_phone = normalize_phone(
        phone
    )

    registered_phone = normalize_phone(
        user.phone
    )

    if (
        entered_phone
        != registered_phone
    ):

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": True,
                "success": False,
                "token": token,
                "message": (
                    "Registered phone number does not match."
                ),
                "user_id": user_id,
                "phone": phone,
            },
        )

    # -----------------------------------------------------
    # PASSWORD MATCH
    # -----------------------------------------------------

    if password != confirm_password:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": True,
                "success": False,
                "token": token,
                "message": (
                    "Passwords do not match."
                ),
                "user_id": user_id,
                "phone": phone,
            },
        )

    # -----------------------------------------------------
    # PASSWORD VALIDATION
    # -----------------------------------------------------

    valid, message = validate_password(
        password
    )

    if not valid:

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": True,
                "success": False,
                "token": token,
                "message": message,
                "user_id": user_id,
                "phone": phone,
            },
        )

    # -----------------------------------------------------
    # UPDATE PASSWORD + MARK TOKEN USED
    # -----------------------------------------------------

    user.password = hash_password(
        password
    )

    reset_token.used_at = (
        datetime.utcnow()
    )

    try:

        db.commit()

    except Exception:

        db.rollback()

        return templates.TemplateResponse(
            "reset-password-admin.html",
            {
                "request": request,
                "valid": True,
                "success": False,
                "token": token,
                "message": (
                    "Unable to reset password. "
                    "Please try again."
                ),
                "user_id": user_id,
                "phone": phone,
            },
        )

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    return templates.TemplateResponse(
        "reset-password-admin.html",
        {
            "request": request,
            "valid": False,
            "success": True,
            "message": (
                "Password changed successfully. "
                "You can now log in with your new password."
            ),
        },
    )