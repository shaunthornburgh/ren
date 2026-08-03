"""One-off data migration: give every event a calendar.

`calendar_id` is becoming required on events. Any pre-existing event with a
NULL `calendar_id` is assigned to a "General" calendar owned by that event's
organizer (created once per organizer, reused on re-runs). Idempotent.

Run inside the backend container:
    docker exec ren-backend python -m scripts.backfill_calendar_ids
"""

from sqlalchemy import select

from app import crud
from app.core.database import SessionLocal
from app.models.event import Event
from app.schemas.calendar import CalendarCreate

DEFAULT_NAME = "General"


def run() -> None:
    db = SessionLocal()
    try:
        orphans = db.scalars(
            select(Event).where(Event.calendar_id.is_(None))
        ).all()
        if not orphans:
            print("No events with a NULL calendar_id — nothing to do.")
            return

        by_organizer: dict[int, list[Event]] = {}
        for event in orphans:
            by_organizer.setdefault(event.organizer_id, []).append(event)

        for organizer_id, events in by_organizer.items():
            existing = [
                c
                for c in crud.calendar.get_multi_by_owner(
                    db, owner_id=organizer_id
                )
                if c.name == DEFAULT_NAME
            ]
            calendar = existing[0] if existing else crud.calendar.create(
                db,
                obj_in=CalendarCreate(
                    name=DEFAULT_NAME,
                    description="Auto-created for previously uncategorised events.",
                ),
                owner_id=organizer_id,
            )
            for event in events:
                event.calendar_id = calendar.id
            db.commit()
            print(
                f"Organizer {organizer_id}: assigned {len(events)} event(s) "
                f"to calendar {calendar.id} ({calendar.slug})."
            )
    finally:
        db.close()


if __name__ == "__main__":
    run()
