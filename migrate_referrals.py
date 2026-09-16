import secrets
import string

from sqlalchemy import text

from database.database import engine


# =========================================================
# CONFIG
# =========================================================

REFERRAL_PREFIX = "CB"
REFERRAL_LENGTH = 8


# =========================================================
# GENERATE UNIQUE REFERRAL CODE
# =========================================================

def generate_referral_code(existing_codes):

    characters = string.ascii_uppercase + string.digits

    while True:

        random_part = "".join(
            secrets.choice(characters)
            for _ in range(REFERRAL_LENGTH)
        )

        code = f"{REFERRAL_PREFIX}{random_part}"

        if code not in existing_codes:
            return code


# =========================================================
# CHECK COLUMN
# =========================================================

def column_exists(connection, table_name, column_name):

    result = connection.execute(
        text(f"PRAGMA table_info({table_name})")
    )

    columns = result.fetchall()

    return any(
        row[1] == column_name
        for row in columns
    )


# =========================================================
# MIGRATION
# =========================================================

def migrate():

    print("")
    print("==========================================")
    print(" CrickBet Referral System Migration")
    print("==========================================")
    print("")

    with engine.begin() as connection:

        # -----------------------------------------------------
        # referral_code
        # -----------------------------------------------------

        if not column_exists(
            connection,
            "users",
            "referral_code"
        ):

            print(
                "Adding users.referral_code..."
            )

            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN referral_code VARCHAR(30)
                    """
                )
            )

        else:

            print(
                "users.referral_code already exists."
            )

        # -----------------------------------------------------
        # referred_by_user_id
        # -----------------------------------------------------

        if not column_exists(
            connection,
            "users",
            "referred_by_user_id"
        ):

            print(
                "Adding users.referred_by_user_id..."
            )

            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN referred_by_user_id INTEGER
                    """
                )
            )

        else:

            print(
                "users.referred_by_user_id already exists."
            )

        # -----------------------------------------------------
        # first_deposit_completed
        # -----------------------------------------------------

        if not column_exists(
            connection,
            "users",
            "first_deposit_completed"
        ):

            print(
                "Adding users.first_deposit_completed..."
            )

            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN first_deposit_completed
                    BOOLEAN DEFAULT 0
                    """
                )
            )

        else:

            print(
                "users.first_deposit_completed already exists."
            )

        # -----------------------------------------------------
        # referral_bonus_paid
        # -----------------------------------------------------

        if not column_exists(
            connection,
            "users",
            "referral_bonus_paid"
        ):

            print(
                "Adding users.referral_bonus_paid..."
            )

            connection.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN referral_bonus_paid
                    BOOLEAN DEFAULT 0
                    """
                )
            )

        else:

            print(
                "users.referral_bonus_paid already exists."
            )

        # -----------------------------------------------------
        # Existing NULL booleans
        # -----------------------------------------------------

        connection.execute(
            text(
                """
                UPDATE users
                SET first_deposit_completed = 0
                WHERE first_deposit_completed IS NULL
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE users
                SET referral_bonus_paid = 0
                WHERE referral_bonus_paid IS NULL
                """
            )
        )

        # -----------------------------------------------------
        # Load existing referral codes
        # -----------------------------------------------------

        result = connection.execute(
            text(
                """
                SELECT referral_code
                FROM users
                WHERE referral_code IS NOT NULL
                """
            )
        )

        existing_codes = {
            row[0]
            for row in result.fetchall()
            if row[0]
        }

        # -----------------------------------------------------
        # Find users without referral codes
        # -----------------------------------------------------

        result = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE referral_code IS NULL
                   OR TRIM(referral_code) = ''
                ORDER BY id ASC
                """
            )
        )

        users_without_codes = result.fetchall()

        print(
            f"Users requiring referral codes: "
            f"{len(users_without_codes)}"
        )

        # -----------------------------------------------------
        # Generate codes
        # -----------------------------------------------------

        for row in users_without_codes:

            user_id = row[0]

            code = generate_referral_code(
                existing_codes
            )

            connection.execute(
                text(
                    """
                    UPDATE users
                    SET referral_code = :code
                    WHERE id = :user_id
                    """
                ),
                {
                    "code": code,
                    "user_id": user_id
                }
            )

            existing_codes.add(code)

            print(
                f"User {user_id} -> {code}"
            )

        # -----------------------------------------------------
        # Unique index
        # -----------------------------------------------------

        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                ux_users_referral_code
                ON users(referral_code)
                """
            )
        )

        # -----------------------------------------------------
        # Index for referred users
        # -----------------------------------------------------

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                ix_users_referred_by_user_id
                ON users(referred_by_user_id)
                """
            )
        )

    print("")
    print("==========================================")
    print(" Migration completed successfully.")
    print("==========================================")
    print("")


if __name__ == "__main__":
    migrate()