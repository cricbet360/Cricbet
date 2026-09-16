from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form
)

from fastapi.responses import RedirectResponse

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database.database import get_db

from models.admin import Admin
from models.employee import Employee
from models.user import User
from models.deposit_request import DepositRequest
from models.withdrawal_request import WithdrawalRequest
from models.password_reset_token import (
    PasswordResetToken,
    generate_reset_token
)

from auth.password import hash_password


router = APIRouter(
    prefix="/admin"
)

templates = Jinja2Templates(
    directory="templates"
)


# =========================================================
# ADMIN AUTH CHECK
# =========================================================

def get_logged_in_admin(
    request: Request,
    db: Session
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


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@router.get("/dashboard")
async def admin_dashboard(

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        request.session.clear()

        return RedirectResponse(
            "/admin/login",
            status_code=303
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
            DepositRequest.status == "Pending"
        )
        .count()
    )

    completed_deposits = (
        db.query(DepositRequest)
        .filter(
            DepositRequest.status == "Completed"
        )
        .count()
    )

    pending_withdrawals = (
        db.query(WithdrawalRequest)
        .filter(
            WithdrawalRequest.status == "Pending"
        )
        .count()
    )

    completed_withdrawals = (
        db.query(WithdrawalRequest)
        .filter(
            WithdrawalRequest.status == "Completed"
        )
        .count()
    )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "admin": admin,
            "employees": employees,

            "pending_deposits":
                pending_deposits,

            "completed_deposits":
                completed_deposits,

            "pending_withdrawals":
                pending_withdrawals,

            "completed_withdrawals":
                completed_withdrawals
        }
    )


# =========================================================
# ALL USERS
# =========================================================

@router.get("/users")
async def admin_users(

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        request.session.clear()

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    users = (
        db.query(User)
        .order_by(
            User.id.desc()
        )
        .all()
    )

    # -----------------------------------------------------
    # Find active reset links
    # -----------------------------------------------------

    now = datetime.utcnow()

    active_reset_tokens = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now
        )
        .all()
    )

    reset_token_map = {}

    for reset_token in active_reset_tokens:

        reset_token_map[
            reset_token.user_id
        ] = reset_token

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "admin": admin,
            "users": users,
            "reset_token_map": reset_token_map
        }
    )


# =========================================================
# GENERATE PASSWORD RESET LINK
# =========================================================

@router.post("/users/{user_id}/reset-password")
async def generate_password_reset_link(

    user_id: int,

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        request.session.clear()

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    # -----------------------------------------------------
    # Find user
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
            "/admin/users?error=User+not+found",
            status_code=303
        )

    # -----------------------------------------------------
    # Invalidate previous unused tokens
    # -----------------------------------------------------

    old_tokens = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None)
        )
        .all()
    )

    now = datetime.utcnow()

    for old_token in old_tokens:

        old_token.used_at = now

    # -----------------------------------------------------
    # Generate secure token
    # -----------------------------------------------------

    token = generate_reset_token()

    expires_at = (
        datetime.utcnow()
        + timedelta(minutes=30)
    )

    reset_token = PasswordResetToken(

        user_id=user.id,

        token=token,

        expires_at=expires_at

    )

    db.add(reset_token)

    db.commit()

    db.refresh(reset_token)

    # -----------------------------------------------------
    # Build reset URL
    # -----------------------------------------------------

    base_url = str(
        request.base_url
    ).rstrip("/")

    reset_url = (
        f"{base_url}"
        f"/reset-password/admin/"
        f"{token}"
    )

    # -----------------------------------------------------
    # Show link to admin
    # -----------------------------------------------------

    return templates.TemplateResponse(
        "admin/reset_password_link.html",
        {
            "request": request,
            "admin": admin,
            "user": user,
            "reset_url": reset_url,
            "expires_at": expires_at
        }
    )


# =========================================================
# CREATE EMPLOYEE
# =========================================================

@router.post("/employees/create")
async def create_employee(

    request: Request,

    employee_id: str = Form(...),

    password: str = Form(...),

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    employee_id = employee_id.strip()

    if len(employee_id) < 3:

        return RedirectResponse(
            "/admin/dashboard?error=Employee+ID+must+be+at+least+3+characters",
            status_code=303
        )

    if len(employee_id) > 50:

        return RedirectResponse(
            "/admin/dashboard?error=Employee+ID+is+too+long",
            status_code=303
        )

    if len(password) < 6:

        return RedirectResponse(
            "/admin/dashboard?error=Password+must+be+at+least+6+characters",
            status_code=303
        )

    existing_employee = (
        db.query(Employee)
        .filter(
            Employee.employee_id == employee_id
        )
        .first()
    )

    if existing_employee:

        return RedirectResponse(
            "/admin/dashboard?error=Employee+ID+already+exists",
            status_code=303
        )

    employee = Employee(

        employee_id=employee_id,

        password=hash_password(
            password
        ),

        status="Active"

    )

    db.add(employee)

    db.commit()

    db.refresh(employee)

    return RedirectResponse(
        "/admin/dashboard?success=Employee+created+successfully",
        status_code=303
    )


# =========================================================
# DEACTIVATE EMPLOYEE
# =========================================================

@router.post(
    "/employees/{employee_id}/deactivate"
)
async def deactivate_employee(

    employee_id: int,

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    employee = (
        db.query(Employee)
        .filter(
            Employee.id == employee_id
        )
        .first()
    )

    if employee:

        employee.status = "Inactive"

        db.commit()

    return RedirectResponse(
        "/admin/dashboard",
        status_code=303
    )


# =========================================================
# ACTIVATE EMPLOYEE
# =========================================================

@router.post(
    "/employees/{employee_id}/activate"
)
async def activate_employee(

    employee_id: int,

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    employee = (
        db.query(Employee)
        .filter(
            Employee.id == employee_id
        )
        .first()
    )

    if employee:

        employee.status = "Active"

        db.commit()

    return RedirectResponse(
        "/admin/dashboard",
        status_code=303
    )


# =========================================================
# ALL DEPOSITS
# =========================================================

@router.get("/deposits")
async def admin_deposits(

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    deposits = (
        db.query(DepositRequest)
        .order_by(
            DepositRequest.created_at.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        "admin/deposits.html",
        {
            "request": request,
            "admin": admin,
            "deposits": deposits
        }
    )


# =========================================================
# ALL WITHDRAWALS
# =========================================================

@router.get("/withdrawals")
async def admin_withdrawals(

    request: Request,

    db: Session = Depends(get_db)

):

    admin = get_logged_in_admin(
        request,
        db
    )

    if not admin:

        return RedirectResponse(
            "/admin/login",
            status_code=303
        )

    withdrawals = (
        db.query(WithdrawalRequest)
        .order_by(
            WithdrawalRequest.created_at.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        "admin/withdrawals.html",
        {
            "request": request,
            "admin": admin,
            "withdrawals": withdrawals
        }
    )