"""One-off admin tool: set a user's role by email (e.g. to make the first admin).

Idempotent. Run inside the backend container:
    docker exec ren-backend python -m scripts.set_user_role <email> <role>

<role> is one of: customer, organizer, admin.
"""

import argparse
import sys

from sqlalchemy import select

from app import models  # noqa: F401 — register all models for relationships
from app.core.database import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a user's role by email.")
    parser.add_argument("email")
    parser.add_argument("role", choices=[r.value for r in UserRole])
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email))
        if user is None:
            sys.exit(f"No user with email {args.email!r}.")
        role = UserRole(args.role)
        if user.role is role:
            print(f"OK: {user.email} is already {role.value}.")
            return
        previous = user.role
        user.role = role
        db.commit()
        print(f"OK: {user.email} changed from {previous.value} to {role.value}.")


if __name__ == "__main__":
    main()
