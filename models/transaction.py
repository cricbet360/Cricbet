from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    amount = Column(Float)

    transaction_type = Column(String)

    status = Column(String, default="Completed")

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    user = relationship(
        "User",
        back_populates="transactions"
    )

