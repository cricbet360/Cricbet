import secrets

from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
)

from fastapi.responses import (
    RedirectResponse,
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database.database import get_db

from models.admin import Admin
from models.employee import Employee
from models.user import User
from models.deposit_request import DepositRequest
from models.withdrawal_request import WithdrawalRequest
from models.password_reset_token import PasswordResetToken

from auth.password import hash_password


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

templates = Jinja2Templates(
    directory="templates"
)


# =========================================================
# CONFIG
# =========================================================

RESET_LINK_EXPIRY_MINUTES = 30


# =========================================================
# ADMIN AUTH
# =========================================================

def get_logged_in_admin(
    request: Request,
    db: Session,
):

    admin_id = request.session.get(
        "admin_id"
    )

    if not admin_id:
        return None

    admin = (
        db.query(Admin)
        .filter(
            Admin.id == admin_id
        )
        .first()
    )

    return admin


def require_admin(
    request: Request,
    db: Session,
):

    admin = get_logged_in_admin(
        request,
        db,
    )

    if not admin:
        return None

    return admin


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@router.get("/dashboard")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    employees = (
        db.query(Employee)
        .order_by(
            Employee.id.desc()
        )
        .all()
    )

    pending_deposits = (
        db.query(DepositRequest)
        .filter(
            DepositRequest.status
            == "Pending"
        )
        .count()
    )

    completed_deposits = (
        db.query(DepositRequest)
        .filter(
            DepositRequest.status
            == "Completed"
        )
        .count()
    )

    pending_withdrawals = (
        db.query(WithdrawalRequest)
        .filter(
            WithdrawalRequest.status
            == "Pending"
        )
        .count()
    )

    completed_withdrawals = (
        db.query(WithdrawalRequest)
        .filter(
            WithdrawalRequest.status
            == "Completed"
        )
        .count()
    )

    user_count = (
        db.query(User)
        .count()
    )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "admin": admin,
            "employees": employees,
            "pending_deposits": pending_deposits,
            "completed_deposits": completed_deposits,
            "pending_withdrawals": pending_withdrawals,
            "completed_withdrawals": completed_withdrawals,
            "user_count": user_count,
        },
    )


# =========================================================
# CREATE EMPLOYEE
# =========================================================

@router.post("/employees/create")
def create_employee(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    username = username.strip()

    existing = (
        db.query(Employee)
        .filter(
            Employee.username
            == username
        )
        .first()
    )

    if existing:

        return RedirectResponse(
            "/admin/dashboard?error=employee_exists",
            status_code=303,
        )

    employee = Employee(
        username=username,
        password=hash_password(
            password
        ),
        status="Active",
    )

    db.add(employee)

    db.commit()

    return RedirectResponse(
        "/admin/dashboard",
        status_code=303,
    )


# =========================================================
# DEACTIVATE EMPLOYEE
# =========================================================

@router.post(
    "/employees/{employee_id}/deactivate"
)
def deactivate_employee(
    request: Request,
    employee_id: int,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    employee = (
        db.query(Employee)
        .filter(
            Employee.id
            == employee_id
        )
        .first()
    )

    if employee:

        employee.status = "Inactive"

        db.commit()

    return RedirectResponse(
        "/admin/dashboard",
        status_code=303,
    )


# =========================================================
# ACTIVATE EMPLOYEE
# =========================================================

@router.post(
    "/employees/{employee_id}/activate"
)
def activate_employee(
    request: Request,
    employee_id: int,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    employee = (
        db.query(Employee)
        .filter(
            Employee.id
            == employee_id
        )
        .first()
    )

    if employee:

        employee.status = "Active"

        db.commit()

    return RedirectResponse(
        "/admin/dashboard",
        status_code=303,
    )


# =========================================================
# DEPOSITS
# =========================================================

@router.get("/deposits")
def admin_deposits(
    request: Request,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    deposits = (
        db.query(DepositRequest)
        .order_by(
            DepositRequest.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        "admin/deposits.html",
        {
            "request": request,
            "admin": admin,
            "deposits": deposits,
        },
    )


# =========================================================
# WITHDRAWALS
# =========================================================

@router.get("/withdrawals")
def admin_withdrawals(
    request: Request,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    withdrawals = (
        db.query(WithdrawalRequest)
        .order_by(
            WithdrawalRequest.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        "admin/withdrawals.html",
        {
            "request": request,
            "admin": admin,
            "withdrawals": withdrawals,
        },
    )


# =========================================================
# USERS
# =========================================================

@router.get("/users")
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    users = (
        db.query(User)
        .order_by(
            User.id.desc()
        )
        .all()
    )

    now = datetime.utcnow()

    # -----------------------------------------------------
    # FIND ACTIVE RESET TOKEN FOR EACH USER
    # -----------------------------------------------------

    reset_tokens = {}

    for user in users:

        reset_token = (
            db.query(
                PasswordResetToken
            )
            .filter(
                PasswordResetToken.user_id
                == user.id,
                PasswordResetToken.used_at
                == None,
            )
            .order_by(
                PasswordResetToken.created_at.desc()
            )
            .first()
        )

        if reset_token:

            if now <= reset_token.expires_at:

                reset_tokens[
                    user.id
                ] = reset_token

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "admin": admin,
            "users": users,
            "reset_tokens": reset_tokens,
        },
    )


# =========================================================
# GENERATE PASSWORD RESET LINK
# =========================================================

@router.post(
    "/users/{user_id}/generate-reset-link"
)
def generate_reset_link(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
):

    admin = require_admin(
        request,
        db,
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )

    # -----------------------------------------------------
    # FIND USER
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        return RedirectResponse(
            "/admin/users?error=user_not_found",
            status_code=303,
        )

    # -----------------------------------------------------
    # INVALIDATE OLD UNUSED TOKENS
    # -----------------------------------------------------

    old_tokens = (
        db.query(
            PasswordResetToken
        )
        .filter(
            PasswordResetToken.user_id
            == user.id,
            PasswordResetToken.used_at
            == None,
        )
        .all()
    )

    now = datetime.utcnow()

    for old_token in old_tokens:

        old_token.used_at = now

    # -----------------------------------------------------
    # GENERATE SECURE TOKEN
    # -----------------------------------------------------

    token = secrets.token_urlsafe(
        48
    )

    expires_at = (
        now
        + timedelta(
            minutes=RESET_LINK_EXPIRY_MINUTES
        )
    )

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )

    db.add(reset_token)

    db.commit()

    # -----------------------------------------------------
    # BUILD RESET URL
    # -----------------------------------------------------
    #
    # Uses the current request host.
    #
    # Example:
    # http://127.0.0.1:8000/reset-password/admin/xxxxx
    #
    # or
    #
    # https://yourdomain.com/reset-password/admin/xxxxx
    # -----------------------------------------------------

    base_url = str(
        request.base_url
    ).rstrip("/")

    reset_link = (
        f"{base_url}"
        f"/reset-password/admin/"
        f"{token}"
    )

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "admin": admin,
            "users": (
                db.query(User)
                .order_by(
                    User.id.desc()
                )
                .all()
            ),
            "reset_tokens": {
                user.id: reset_token
            },
            "generated_user": user,
            "reset_link": reset_link,
            "reset_expiry": expires_at,
        },
    )