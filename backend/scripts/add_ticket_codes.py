"""One-off schema migration: add check-in codes to tickets.

`Base.metadata.create_all` only creates missing tables, so an existing
`tickets` table never gains the new columns. This adds `code` and
`checked_in_at`, backfills a unique code for every existing ticket, then makes
`code` NOT NULL with a unique index (the same `ix_tickets_code` the model
declares).

Idempotent. Run inside the backend container:
    docker exec ren-backend python -m scripts.add_ticket_codes
"""

from sqlalchemy import text

from app.core.database import engine
from app.models.ticket import TICKET_CODE_LENGTH, generate_ticket_code


def run() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS code "
                f"VARCHAR({TICKET_CODE_LENGTH})"
            )
        )
        print("OK: code column")
        conn.execute(
            text(
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS checked_in_at "
                "TIMESTAMP WITH TIME ZONE"
            )
        )
        print("OK: checked_in_at column")

        ids = conn.execute(
            text("SELECT id FROM tickets WHERE code IS NULL")
        ).scalars().all()
        used = set(
            conn.execute(
                text("SELECT code FROM tickets WHERE code IS NOT NULL")
            ).scalars().all()
        )
        for ticket_id in ids:
            code = generate_ticket_code()
            while code in used:
                code = generate_ticket_code()
            used.add(code)
            conn.execute(
                text("UPDATE tickets SET code = :code WHERE id = :id"),
                {"code": code, "id": ticket_id},
            )
        print(f"OK: backfilled {len(ids)} ticket code(s)")

        conn.execute(text("ALTER TABLE tickets ALTER COLUMN code SET NOT NULL"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_tickets_code "
                "ON tickets (code)"
            )
        )
        print("OK: code NOT NULL + unique index")
    print("Done.")


if __name__ == "__main__":
    run()
