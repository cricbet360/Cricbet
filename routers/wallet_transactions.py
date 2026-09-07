import os
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import (
    APIRouter,
    Request,
    Depends,
    UploadFile,
    File,
    Form,
)

from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from database.database import get_db

from models.user import User
from models.wallet import Wallet
from models.deposit_request import DepositRequest
from models.withdrawal_request import WithdrawalRequest


router = APIRouter()


# ==========================================================
# SETTINGS
# ==========================================================

UPLOAD_DIR = "static/uploads/payment_screenshots"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


MIN_DEPOSIT = Decimal("100.00")
MAX_DEPOSIT = Decimal("100000.00")

MIN_WITHDRAW = Decimal("100.00")
MAX_WITHDRAW = Decimal("100000.00")

MAX_FILE_SIZE = 5 * 1024 * 1024


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# ==========================================================
# GET CURRENT USER
# ==========================================================

def get_current_user(
    request: Request,
    db: Session,
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:
        return None

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    return user


# ==========================================================
# CONVERT AMOUNT
# ==========================================================

def parse_amount(
    amount: str
):

    try:

        value = Decimal(
            str(amount)
        ).quantize(
            Decimal("0.01")
        )

        return value

    except (
        InvalidOperation,
        ValueError,
        TypeError
    ):

        return None


# ==========================================================
# DEPOSIT
# ==========================================================

@router.post(
    "/api/wallet/deposit"
)
async def submit_deposit(
    request: Request,

    amount: str = Form(...),

    utr_number: str = Form(...),

    payment_screenshot: UploadFile = File(...),

    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    user = get_current_user(
        request,
        db
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message":
                    "Please login first."
            }
        )


    # ------------------------------------------------------
    # AMOUNT
    # ------------------------------------------------------

    deposit_amount = parse_amount(
        amount
    )

    if deposit_amount is None:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid deposit amount."
            }
        )


    if deposit_amount < MIN_DEPOSIT:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Minimum deposit is ₹100."
            }
        )


    if deposit_amount > MAX_DEPOSIT:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Maximum deposit is ₹100000."
            }
        )


    # ------------------------------------------------------
    # UTR
    # ------------------------------------------------------

    utr_number = (
        utr_number.strip()
    )


    if not utr_number:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "UTR number is required."
            }
        )


    if len(utr_number) < 6 or len(utr_number) > 100:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid UTR number."
            }
        )


    # ------------------------------------------------------
    # SCREENSHOT
    # ------------------------------------------------------

    if not payment_screenshot.filename:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Payment screenshot is required."
            }
        )


    original_name = (
        payment_screenshot.filename
        or ""
    )


    extension = os.path.splitext(
        original_name
    )[1].lower()


    if extension not in ALLOWED_EXTENSIONS:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Only JPG, JPEG, PNG and WEBP images are allowed."
            }
        )


    # ------------------------------------------------------
    # READ FILE
    # ------------------------------------------------------

    content = await payment_screenshot.read()


    if len(content) == 0:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Screenshot file is empty."
            }
        )


    if len(content) > MAX_FILE_SIZE:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Screenshot must be smaller than 5 MB."
            }
        )


    # ------------------------------------------------------
    # BASIC IMAGE SIGNATURE VALIDATION
    # ------------------------------------------------------

    valid_signature = False


    if content.startswith(
        b"\xff\xd8\xff"
    ):

        valid_signature = True


    elif content.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):

        valid_signature = True


    elif (
        content.startswith(b"RIFF")
        and content[8:12] == b"WEBP"
    ):

        valid_signature = True


    if not valid_signature:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid image file."
            }
        )


    # ------------------------------------------------------
    # SAVE SCREENSHOT
    # ------------------------------------------------------

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )


    filepath = os.path.join(
        UPLOAD_DIR,
        filename
    )


    try:

        with open(
            filepath,
            "wb"
        ) as file:

            file.write(content)

    except Exception:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message":
                    "Could not save screenshot."
            }
        )


    # ------------------------------------------------------
    # CREATE DEPOSIT REQUEST
    # ------------------------------------------------------

    deposit = DepositRequest(

        user_id=user.id,

        amount=deposit_amount,

        screenshot_path=filepath,

        utr_number=utr_number,

        status="Pending",

    )


    db.add(deposit)


    try:

        db.commit()

        db.refresh(deposit)

    except Exception:

        db.rollback()

        # Remove uploaded file if DB failed

        try:

            if os.path.exists(filepath):

                os.remove(filepath)

        except Exception:

            pass


        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message":
                    "Could not create deposit request."
            }
        )


    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    return {

        "success": True,

        "message":
            "Deposit request submitted successfully. It is waiting for employee verification.",

        "deposit_id":
            deposit.id,

        "status":
            deposit.status,

    }


# ==========================================================
# WITHDRAW
# ==========================================================

@router.post(
    "/api/wallet/withdraw"
)
async def submit_withdraw(
    request: Request,

    amount: str = Form(...),

    account_holder_name: str = Form(...),

    bank_name: str = Form(...),

    account_number: str = Form(...),

    ifsc_code: str = Form(...),

    db: Session = Depends(get_db),
):

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------

    user = get_current_user(
        request,
        db
    )

    if not user:

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message":
                    "Please login first."
            }
        )


    # ------------------------------------------------------
    # AMOUNT
    # ------------------------------------------------------

    withdrawal_amount = parse_amount(
        amount
    )


    if withdrawal_amount is None:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid withdrawal amount."
            }
        )


    if withdrawal_amount < MIN_WITHDRAW:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Minimum withdrawal is ₹100."
            }
        )


    if withdrawal_amount > MAX_WITHDRAW:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Maximum withdrawal is ₹100000."
            }
        )


    # ------------------------------------------------------
    # BANK DETAILS
    # ------------------------------------------------------

    account_holder_name = (
        account_holder_name.strip()
    )

    bank_name = (
        bank_name.strip()
    )

    account_number = (
        account_number.strip()
    )

    ifsc_code = (
        ifsc_code.strip()
        .upper()
    )


    if not account_holder_name:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Account holder name is required."
            }
        )


    if len(account_holder_name) > 150:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Account holder name is too long."
            }
        )


    if not bank_name:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Bank name is required."
            }
        )


    if len(bank_name) > 150:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Bank name is too long."
            }
        )


    # ------------------------------------------------------
    # ACCOUNT NUMBER
    # ------------------------------------------------------

    if (
        not account_number.isdigit()
        or not 8 <= len(account_number) <= 20
    ):

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid account number."
            }
        )


    # ------------------------------------------------------
    # IFSC
    # ------------------------------------------------------

    if (
        len(ifsc_code) != 11
        or not ifsc_code.isalnum()
        or ifsc_code[4] != "0"
        or not ifsc_code[:4].isalpha()
    ):

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Invalid IFSC code."
            }
        )


    # ------------------------------------------------------
    # GET WALLET
    # ------------------------------------------------------

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == user.id
        )
        .first()
    )


    if wallet is None:

        wallet = Wallet(
            user_id=user.id,
            balance=Decimal("0.00"),
            exposure=Decimal("0.00")
        )

        db.add(wallet)

        db.flush()


    # ------------------------------------------------------
    # BALANCE
    # ------------------------------------------------------

    current_balance = (
        wallet.balance or Decimal("0.00")
    )


    if withdrawal_amount > current_balance:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message":
                    "Insufficient balance."
            }
        )


    # ------------------------------------------------------
    # RESERVE WITHDRAWAL AMOUNT
    #
    # The amount is removed from available balance now
    # so the user cannot submit another withdrawal using
    # the same money.
    #
    # It will NOT be deducted again when employee completes.
    # ------------------------------------------------------

    wallet.balance = (
        current_balance
        - withdrawal_amount
    )


    # ------------------------------------------------------
    # CREATE WITHDRAWAL REQUEST
    # ------------------------------------------------------

    withdrawal = WithdrawalRequest(

        user_id=user.id,

        amount=withdrawal_amount,

        account_holder_name=
            account_holder_name,

        bank_name=
            bank_name,

        account_number=
            account_number,

        ifsc_code=
            ifsc_code,

        status="Pending",

    )


    db.add(withdrawal)


    try:

        db.commit()

        db.refresh(withdrawal)

        db.refresh(wallet)

    except Exception:

        db.rollback()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message":
                    "Could not create withdrawal request."
            }
        )


    # ------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------

    return {

        "success": True,

        "message":
            "Withdrawal request submitted successfully and is waiting for employee processing.",

        "withdrawal_id":
            withdrawal.id,

        "status":
            withdrawal.status,

        "balance":
            float(wallet.balance),

    }