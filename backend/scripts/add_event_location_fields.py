"""One-off schema migration: split event location into online / in-person.

`Base.metadata.create_all` only creates missing tables, so an existing `events`
table never gains the new columns. This adds them, and widens `location` to
512 chars so it can hold a joining URL with query parameters.

Existing rows keep their `location` text and default to `is_online = false`
with NULL coordinates. Those rows stay readable — the strict "in-person needs
lat/lng" rule only applies when an event is created or its location edited.

Idempotent. Run inside the backend container:
    docker exec ren-backend python -m scripts.add_event_location_fields
"""

from sqlalchemy import text

from app.core.database import engine

STATEMENTS = [
    (
        "is_online column",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS is_online "
        "BOOLEAN NOT NULL DEFAULT false",
    ),
    (
        "lat column",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION",
    ),
    (
        "lng column",
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION",
    ),
    (
        "location widened to 512",
        "ALTER TABLE events ALTER COLUMN location TYPE VARCHAR(512)",
    ),
]


def run() -> None:
    with engine.begin() as conn:
        for label, sql in STATEMENTS:
            conn.execute(text(sql))
            print(f"OK: {label}")
    print("Done.")


if __name__ == "__main__":
    run()
