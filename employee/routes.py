from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import (
    APIRouter,
    Request,
    Depends
)

from fastapi.responses import RedirectResponse

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database.database import get_db

from models.employee import Employee
from models.deposit_request import DepositRequest
from models.withdrawal_request import WithdrawalRequest
from models.user import User
from models.transaction import Transaction


router = APIRouter(
    prefix="/employee"
)

templates = Jinja2Templates(
    directory="templates"
)


# =========================================================
# BONUS CONFIGURATION
# =========================================================

DEPOSIT_BONUS_RATE = Decimal("0.10")
REFERRAL_BONUS_RATE = Decimal("0.10")


# =========================================================
# MONEY HELPER
# =========================================================

def money(value):

    return Decimal(
        str(value or 0)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# =========================================================
# EMPLOYEE AUTH CHECK
# =========================================================

def get_logged_in_employee(
    request: Request,
    db: Session
):

    employee_id = request.session.get(
        "employee_id"
    )

    if not employee_id:
        return None

    employee = (
        db.query(Employee)
        .filter(
            Employee.id == employee_id
        )
        .first()
    )

    if not employee:
        return None

    if employee.status != "Active":
        return None

    return employee


# =========================================================
# EMPLOYEE DASHBOARD
# =========================================================

@router.get("/dashboard")
async def employee_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    employee = get_logged_in_employee(
        request,
        db
    )

    if not employee:

        return RedirectResponse(
            "/employee/login",
            status_code=303
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
        "employee/dashboard.html",
        {
            "request": request,
            "employee": employee,
            "pending_deposits": pending_deposits,
            "completed_deposits": completed_deposits,
            "pending_withdrawals": pending_withdrawals,
            "completed_withdrawals": completed_withdrawals,
        }
    )


# =========================================================
# PENDING DEPOSITS
# =========================================================

@router.get("/deposits")
async def employee_deposits(
    request: Request,
    db: Session = Depends(get_db)
):

    employee = get_logged_in_employee(
        request,
        db
    )

    if not employee:

        return RedirectResponse(
            "/employee/login",
            status_code=303
        )

    deposits = (
        db.query(DepositRequest)
        .filter(
            DepositRequest.status == "Pending"
        )
        .order_by(
            DepositRequest.created_at.asc()
        )
        .all()
    )

    return templates.TemplateResponse(
        "employee/deposits.html",
        {
            "request": request,
            "employee": employee,
            "deposits": deposits
        }
    )


# =========================================================
# COMPLETE DEPOSIT
# =========================================================

@router.post("/deposits/{deposit_id}/done")
async def complete_deposit(

    deposit_id: int,

    request: Request,

    db: Session = Depends(get_db)

):

    employee = get_logged_in_employee(
        request,
        db
    )

    if not employee:

        return RedirectResponse(
            "/employee/login",
            status_code=303
        )

    try:

        # =====================================================
        # LOCK DEPOSIT
        # =====================================================

        deposit = (
            db.query(DepositRequest)
            .filter(
                DepositRequest.id == deposit_id
            )
            .with_for_update()
            .first()
        )

        if not deposit:

            db.rollback()

            return RedirectResponse(
                "/employee/deposits",
                status_code=303
            )

        # =====================================================
        # PREVENT DOUBLE PROCESSING
        # =====================================================

        if deposit.status != "Pending":

            db.rollback()

            return RedirectResponse(
                "/employee/deposits",
                status_code=303
            )

        # =====================================================
        # VALIDATE AMOUNT
        # =====================================================

        deposit_amount = money(
            deposit.amount
        )

        if deposit_amount <= Decimal("0.00"):

            db.rollback()

            return RedirectResponse(
                "/employee/deposits",
                status_code=303
            )

        # =====================================================
        # LOCK USER
        # =====================================================

        user = (
            db.query(User)
            .filter(
                User.id == deposit.user_id
            )
            .with_for_update()
            .first()
        )

        if not user:

            db.rollback()

            return RedirectResponse(
                "/employee/deposits",
                status_code=303
            )

        # =====================================================
        # FIRST DEPOSIT CHECK
        # =====================================================

        is_first_deposit = not bool(
            user.first_deposit_completed
        )

        # =====================================================
        # USER BALANCE
        # =====================================================

        user_balance_before = money(
            user.balance
        )

        # =====================================================
        # ORIGINAL DEPOSIT
        # =====================================================

        user.balance = float(
            user_balance_before
            + deposit_amount
        )

        deposit_transaction = Transaction(

            user_id=user.id,

            amount=deposit_amount,

            transaction_type="DEPOSIT",

            status="Completed",

            reference_type="DepositRequest",

            reference_id=deposit.id,

            description=(
                "Deposit approved - "
                f"UTR {deposit.utr_number}"
            )
        )

        db.add(
            deposit_transaction
        )

        # =====================================================
        # 10% DEPOSIT BONUS
        #
        # EVERY APPROVED DEPOSIT GETS THIS.
        # =====================================================

        deposit_bonus = (
            deposit_amount
            * DEPOSIT_BONUS_RATE
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if deposit_bonus > Decimal("0.00"):

            bonus_balance_before = money(
                user.balance
            )

            user.balance = float(
                bonus_balance_before
                + deposit_bonus
            )

            deposit_bonus_transaction = Transaction(

                user_id=user.id,

                amount=deposit_bonus,

                transaction_type="DEPOSIT_BONUS",

                status="Completed",

                reference_type="DepositRequest",

                reference_id=deposit.id,

                description=(
                    "10% deposit bonus"
                )
            )

            db.add(
                deposit_bonus_transaction
            )

        # =====================================================
        # FIRST DEPOSIT REFERRAL BONUS
        # =====================================================

        if is_first_deposit:

            # -------------------------------------------------
            # Mark first deposit immediately.
            #
            # Everything is inside one transaction, so if
            # anything fails, rollback restores this.
            # -------------------------------------------------

            user.first_deposit_completed = True

            # -------------------------------------------------
            # If user has a valid referrer and the referral
            # bonus has not already been paid.
            # -------------------------------------------------

            if (
                user.referred_by_user_id
                and not user.referral_bonus_paid
            ):

                # ---------------------------------------------
                # SECURITY: don't allow self-referral
                # ---------------------------------------------

                if (
                    user.referred_by_user_id
                    != user.id
                ):

                    referrer = (
                        db.query(User)
                        .filter(
                            User.id
                            == user.referred_by_user_id
                        )
                        .with_for_update()
                        .first()
                    )

                    if referrer:

                        referral_bonus = (
                            deposit_amount
                            * REFERRAL_BONUS_RATE
                        ).quantize(
                            Decimal("0.01"),
                            rounding=ROUND_HALF_UP
                        )

                        if (
                            referral_bonus
                            > Decimal("0.00")
                        ):

                            referrer_balance_before = money(
                                referrer.balance
                            )

                            referrer.balance = float(
                                referrer_balance_before
                                + referral_bonus
                            )

                            referral_transaction = Transaction(

                                user_id=referrer.id,

                                amount=referral_bonus,

                                transaction_type="REFERRAL_BONUS",

                                status="Completed",

                                reference_type="DepositRequest",

                                reference_id=deposit.id,

                                description=(
                                    "10% one-time referral bonus "
                                    f"from {user.username}'s "
                                    "first deposit"
                                )
                            )

                            db.add(
                                referral_transaction
                            )

                        # -------------------------------------
                        # Consume referral reward permanently.
                        # -------------------------------------

                        user.referral_bonus_paid = True

            else:

                # -------------------------------------------------
                # No referrer or already consumed.
                # First deposit is still completed.
                # -------------------------------------------------

                user.referral_bonus_paid = True

        # =====================================================
        # COMPLETE DEPOSIT REQUEST
        # =====================================================

        deposit.status = "Completed"

        deposit.processed_by = employee.id

        deposit.completed_at = datetime.utcnow()

        # =====================================================
        # SINGLE ATOMIC COMMIT
        # =====================================================

        db.commit()

        return RedirectResponse(
            "/employee/deposits",
            status_code=303
        )

    except Exception:

        db.rollback()

        return RedirectResponse(
            "/employee/deposits",
            status_code=303
        )


# =========================================================
# TEMPORARY TEST DEPOSIT
# =========================================================

@router.get("/test/create-deposit")
async def create_test_deposit(

    request: Request,

    db: Session = Depends(get_db)

):

    employee = get_logged_in_employee(
        request,
        db
    )

    if not employee:

        return RedirectResponse(
            "/employee/login",
            status_code=303
        )

    user = (
        db.query(User)
        .order_by(
            User.id.asc()
        )
        .first()
    )

    if not user:

        return RedirectResponse(
            "/employee/dashboard",
            status_code=303
        )

    test_deposit = DepositRequest(

        user_id=user.id,

        amount=500.00,

        utr_number="TEST-DEPOSIT-001",

        payment_screenshot="test-payment.png",

        status="Pending"
    )

    db.add(
        test_deposit
    )

    db.commit()

    return RedirectResponse(
        "/employee/deposits",
        status_code=303
    )