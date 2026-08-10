from database.database import SessionLocal
from models.admin import Admin
from auth.password import hash_password

db = SessionLocal()

admin = Admin(
    username="Surya",
    password=hash_password("1234")
)

db.add(admin)
db.commit()

print("✅ Admin created successfully!")