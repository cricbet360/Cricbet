from sqlalchemy import Column, Integer, String

from database.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False)

    password = Column(String(255), nullable=False)