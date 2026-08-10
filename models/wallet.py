from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from database.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    balance = Column(Float, default=0.0)

    exposure = Column(Float, default=0.0)

    user = relationship(
        "User",
        back_populates="wallet"
    )