from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from database.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(50),
        unique=True,
        nullable=False
    )

    email = Column(
        String(100),
        unique=True,
        nullable=False
    )

    phone = Column(
        String(20),
        unique=True,
        nullable=False
    )

    password = Column(
        String(255),
        nullable=False
    )

    balance = Column(
        Float,
        default=10000.00,
        nullable=False
    )

    status = Column(
        String(20),
        default="Active",
        nullable=False
    )

    # =========================================================
    # REFERRAL SYSTEM
    # =========================================================

    # Every user gets a unique referral code.
    # Example: CB7K2P9QX
    referral_code = Column(
        String(30),
        unique=True,
        nullable=True,
        index=True
    )

    # ID of the user who referred this user.
    referred_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    # True after this user's first approved deposit.
    first_deposit_completed = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # True after the one-time referral bonus has been
    # processed for this user.
    referral_bonus_paid = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # =========================================================
    # REFERRER
    # =========================================================

    referrer = relationship(
        "User",
        foreign_keys=[referred_by_user_id],
        remote_side=[id],
        backref="referred_users"
    )

    # =========================================================
    # WALLET
    # =========================================================

    wallet = relationship(
        "Wallet",
        back_populates="user",
        uselist=False
    )

    # =========================================================
    # TRANSACTIONS
    # =========================================================

    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Transaction.created_at.desc()",
    )

    # =========================================================
    # BETS
    # =========================================================

    bets = relationship(
        "Bet",
        back_populates="user",
        order_by="Bet.created_at.desc()",
        cascade="all, delete-orphan",
    )

    # =========================================================
    # DEPOSITS
    # =========================================================

    deposit_requests = relationship(
        "DepositRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="DepositRequest.created_at.desc()",
    )

    # =========================================================
    # WITHDRAWALS
    # =========================================================

    withdrawal_requests = relationship(
        "WithdrawalRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="WithdrawalRequest.created_at.desc()",
    )