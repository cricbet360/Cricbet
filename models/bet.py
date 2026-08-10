from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database.database import Base


class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    stake = Column(
        Float,
        nullable=False
    )

    total_odds = Column(
        Float,
        nullable=False
    )

    potential_win = Column(
        Float,
        nullable=False
    )

    status = Column(
        String,
        default="pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship("User")