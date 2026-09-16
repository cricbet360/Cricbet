from database.database import Base, engine

from models.password_reset_token import PasswordResetToken


print("Creating missing database tables...")

Base.metadata.create_all(
    bind=engine
)

print("Done.")