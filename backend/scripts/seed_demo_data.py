"""Local development seed: fill the database with realistic demo data.

LOCAL / DEV ONLY. Creates six public calendars, ~20 events (past, happening
now, upcoming; published / draft / cancelled; in-person and online), ticket
types with varied stock, hosts, agendas, FAQs, registration questions, orders
(paid, pending, cancelled) with issued + checked-in tickets, calendar
followers, notifications and an event message history.

Everything is generated relative to "now", so past/upcoming stays meaningful
whenever it runs. Purchases go through ``crud.order.create`` / ``fulfill`` /
``release`` — the same path as a real checkout — so inventory, ticket codes and
registration answers behave exactly as they would in the app.

Demo rows are identified by the calendar slugs below and by the
``@demo.ren-events.com`` email domain. The four login accounts are kept (their
password and role are reset) but never deleted.

Run inside the backend container:
    docker exec ren-backend python -m scripts.seed_demo_data           # seed once
    docker exec ren-backend python -m scripts.seed_demo_data --reset   # wipe + reseed

Logins (password ``password123``): organizer@, buyer@, buyer2@, host@
ren-events.com.
"""

import argparse
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import crud
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    AgendaItem,
    Calendar,
    CalendarFollower,
    Event,
    EventFaqItem,
    EventHost,
    EventMessage,
    EventStatus,
    HostRole,
    HostStatus,
    Notification,
    Order,
    OrderItem,
    OrderStatus,
    RegistrationFieldType,
    RegistrationQuestion,
    Ticket,
    TicketStatus,
    TicketType,
    User,
    UserRole,
)
from app.schemas.event import validate_location
from app.schemas.order import OrderCreate, OrderItemCreate
from app.schemas.registration_question import RegistrationAnswerInput

PASSWORD = "password123"
DEMO_DOMAIN = "demo.ren-events.com"

rng = random.Random(2026)  # deterministic: same data on every reseed
NOW = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def at(days: float, hour: int, minute: int = 0) -> datetime:
    """A UTC datetime ``days`` from today at ``hour:minute``."""
    return (NOW + timedelta(days=days)).replace(hour=hour, minute=minute)


def img(seed: str) -> str:
    """A stable, distinct placeholder photo per seed."""
    return f"https://picsum.photos/seed/ren-{seed}/1200/630"


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------

LOGINS = [
    # key, email, name, role
    ("organizer", "organizer@ren-events.com", "Olivia Grant", UserRole.ORGANIZER),
    ("buyer", "buyer@ren-events.com", "Ben Carter", UserRole.CUSTOMER),
    ("host", "host@ren-events.com", "Hana Mori", UserRole.CUSTOMER),
    ("buyer2", "buyer2@ren-events.com", "Sofia Alvarez", UserRole.CUSTOMER),
]

DEMO_PEOPLE = [
    ("jules", "Jules Okafor", UserRole.ORGANIZER),  # runs the comedy calendar
    ("priya", "Priya Shah", UserRole.CUSTOMER),
    ("tom", "Tom Becker", UserRole.CUSTOMER),
    ("amara", "Amara Nwosu", UserRole.CUSTOMER),
    ("liam", "Liam O'Connell", UserRole.CUSTOMER),
    ("mei", "Mei Lin", UserRole.CUSTOMER),
    ("noah", "Noah Fischer", UserRole.CUSTOMER),
    ("zara", "Zara Hussain", UserRole.CUSTOMER),
    ("ethan", "Ethan Brooks", UserRole.CUSTOMER),
    ("chloe", "Chloé Martin", UserRole.CUSTOMER),
    ("kofi", "Kofi Mensah", UserRole.CUSTOMER),
    ("isla", "Isla Campbell", UserRole.CUSTOMER),
]

# --------------------------------------------------------------------------
# Calendars
# --------------------------------------------------------------------------

CALENDARS = [
    # key, slug, name, owner, description, followers
    ("music", "ren-live-music", "Ren Live Music", "organizer",
     "Club nights, rooftop jazz and the best new bands — live music picked by the Ren team.",
     ["buyer", "priya", "tom", "mei", "liam", "zara"]),
    ("tech", "ren-tech-talks", "Ren Tech Talks", "organizer",
     "Meetups, workshops and a yearly summit for people who build software.",
     ["buyer", "host", "noah", "ethan", "priya", "kofi"]),
    ("food", "ren-supper-club", "Ren Supper Club", "organizer",
     "Tasting menus, street food and long tables with strangers who become friends.",
     ["buyer", "amara", "chloe", "isla"]),
    ("comedy", "late-laughs-comedy", "Late Laughs Comedy", "jules",
     "Stand-up from first-timers to headliners, every month across the UK.",
     ["buyer2", "tom", "liam", "zara", "ethan"]),
    ("sport", "ren-sport-social", "Ren Sport & Social", "organizer",
     "Social runs, five-a-side and taster sessions — sport for everyone.",
     ["buyer2", "kofi", "noah", "isla"]),
    ("community", "ren-community", "Ren Community", "organizer",
     "Repair cafés, book clubs and garden days organised by and for neighbours.",
     ["host", "buyer2", "amara", "mei", "chloe"]),
]
DEMO_CALENDAR_SLUGS = [c[1] for c in CALENDARS]

# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------
# Venue: (address, lat, lng) for in-person, or an https URL for online.
# Ticket types: (name, price, quantity, max_per_order, description).
# "sold_out" / "low" name ticket types whose remaining stock is forced to 0 / n
# after sales. "orders" is how many random extra orders to generate.

EVENTS = [
    # ---------------- music ----------------
    dict(
        key="midnight", calendar="music",
        title="Midnight Frequencies: Techno All-Nighter",
        description="Eight hours of relentless techno across two rooms, with a "
        "headline set from Berlin's finest and a full light installation.",
        start=at(-21, 22), hours=8, status=EventStatus.PUBLISHED,
        venue=("Hangar 7, 12 Canal Wharf, London E14 9SR", 51.5045, -0.0235),
        tickets=[("General Admission", 25, 300, 6, "Entry to both rooms."),
                 ("VIP", 60, 40, 4, "Mezzanine access and a welcome drink.")],
        orders=22,
        faq=[("Is there a cloakroom?", "Yes — £3 per item, card only."),
             ("What's the age limit?", "18+. Bring photo ID.")],
    ),
    dict(
        key="jazz", calendar="music",
        title="Jazz on the Roof",
        description="A sunset quartet on a rooftop terrace overlooking the "
        "city. Standards, originals and a little bossa nova.",
        start=at(2, 18, 30), hours=3, status=EventStatus.PUBLISHED,
        venue=("Skyline Terrace, 1 Poultry, London EC2R 8EJ", 51.5133, -0.0906),
        tickets=[("General Admission", 30, 80, 4, None),
                 ("VIP Table", 90, 10, 2, "Reserved table for two with sharing plates.")],
        sold_out=["General Admission"], low={"VIP Table": 2},
        orders=12,
        agenda=[(0, 45, "Set one: Standards", "The Ella Hart Quartet"),
                (60, 45, "Set two: Originals", "The Ella Hart Quartet"),
                (120, 40, "Late set: Bossa & ballads", None)],
        faq=[("What if it rains?", "We move under the terrace canopy — the show goes on."),
             ("Is there a dress code?", "Smart casual.")],
        message=("Doors, weather & table times",
                 "Doors open at 18:00. The forecast looks dry, but bring a layer "
                 "— it gets breezy up there after sunset. VIP tables are held "
                 "until 19:00."),
    ),
    dict(
        key="indie", calendar="music",
        title="Indie Showcase: Five Bands, One Night",
        description="Five of the north's most exciting new bands on one bill. "
        "Come early for the openers — you'll brag about it later.",
        start=at(30, 19), hours=5, status=EventStatus.PUBLISHED,
        venue=("Albert Hall, 27 Peter St, Manchester M2 5QR", 53.4779, -2.2477),
        tickets=[("Early Bird", 12, 50, 4, None),
                 ("General Admission", 18, 400, 6, None)],
        sold_out=["Early Bird"],
        orders=10,
    ),
    dict(
        key="filmscores", calendar="music",
        title="Orchestral Film Scores Live",
        description="A 60-piece orchestra performs the great film themes of "
        "the last fifty years.",
        start=at(75, 19, 30), hours=2.5, status=EventStatus.DRAFT,
        venue=("Symphony Hall, Broad St, Birmingham B1 2EA", 52.4786, -1.9094),
        tickets=[("Stalls", 45, 600, 6, None), ("Circle", 35, 400, 6, None)],
    ),
    # ---------------- tech ----------------
    dict(
        key="vuemeetup", calendar="tech",
        title="Vue & Nuxt Meetup #14",
        description="Two talks, pizza and plenty of time to chat. This month: "
        "Nuxt server components in production and testing Vue with Vitest.",
        start=at(-9, 18, 30), hours=3, status=EventStatus.PUBLISHED,
        venue=("Engine Shed, Station Approach, Bristol BS1 6QH", 51.4489, -2.5813),
        tickets=[("Free RSVP", 0, 120, 1, "Pizza included.")],
        orders=30,
        agenda=[(0, 30, "Doors, pizza & hellos", None),
                (30, 30, "Nuxt server components in production", "Hana Mori"),
                (65, 30, "Testing Vue with Vitest", "Noah Fischer"),
                (100, 60, "Drinks & networking", None)],
        faq=[("Will talks be recorded?", "Yes — they'll be on our YouTube channel within a week."),
             ("Is there step-free access?", "Yes, via the lift by the main entrance.")],
        hosts=[("host", HostRole.HOST)],
    ),
    dict(
        key="postgres", calendar="tech",
        title="Postgres Performance Deep Dive (Online)",
        description="A live, hands-on session on reading EXPLAIN plans, "
        "indexing strategy and fixing the queries that page you at 3am.",
        start=at(1, 17), hours=2, status=EventStatus.PUBLISHED,
        venue="https://zoom.us/j/81234567890",
        tickets=[("Live + recording", 15, 500, 1, None)],
        orders=14,
        questions=[("What do you most want to learn?", RegistrationFieldType.TEXTAREA, False,
                    ["Reading EXPLAIN ANALYZE output", "When partial indexes pay off",
                     "Tuning autovacuum", "Why my ORM queries are slow"])],
    ),
    dict(
        key="aisummit", calendar="tech",
        title="AI Engineering Summit",
        description="Two days of talks and workshops on shipping LLM-powered "
        "products: evals, agents, retrieval and the ops nobody talks about.",
        start=at(45, 9), hours=32, status=EventStatus.PUBLISHED,
        venue=("QEII Centre, Broad Sanctuary, London SW1P 3EE", 51.5005, -0.1290),
        tickets=[("Early Bird", 199, 100, 2, "Limited first-release pricing."),
                 ("General Admission", 299, 400, 4, None),
                 ("VIP", 549, 30, 2, "Speaker dinner and reserved seating.")],
        sold_out=["Early Bird"], low={"VIP": 3},
        orders=18,
        agenda=[(0, 30, "Registration & coffee", None),
                (30, 45, "Keynote: Evals are the product", "Priya Shah"),
                (90, 45, "Agents in production: lessons from a year of outages", "Ethan Brooks"),
                (150, 60, "Lunch", None),
                (210, 90, "Workshop: Retrieval that actually retrieves", "Mei Lin")],
        faq=[("Is lunch included?", "Yes, both days, with vegetarian and vegan options."),
             ("Can I transfer my ticket?", "Yes, up to 48 hours before — email the team."),
             ("Will slides be shared?", "Slides and recordings go to all attendees after the event.")],
        questions=[("Company", RegistrationFieldType.TEXT, True,
                    ["Monzo", "Octopus Energy", "Freelance", "Wise", "Deliveroo", "BBC"]),
                   ("Job title", RegistrationFieldType.TEXT, False,
                    ["Staff Engineer", "ML Engineer", "Engineering Manager", "CTO"]),
                   ("LinkedIn profile", RegistrationFieldType.URL, False,
                    ["https://www.linkedin.com/in/demo-attendee"])],
        hosts=[("priya", HostRole.MANAGER)],
        pending_host=("speakers@example.org", "Guest Speaker Team"),
    ),
    dict(
        key="rust", calendar="tech",
        title="Rust for Pythonistas Workshop",
        description="A half-day, hands-on intro to Rust for people who think "
        "in Python. Ownership explained without the tears.",
        start=at(20, 13), hours=4, status=EventStatus.DRAFT,
        venue="https://meet.google.com/rst-pyth-onx",
        tickets=[("Workshop seat", 49, 40, 1, None)],
    ),
    # ---------------- food ----------------
    dict(
        key="tasting", calendar="food",
        title="Seven-Course Tasting: Autumn Harvest",
        description="A seasonal tasting menu from chef Amara Nwosu, with "
        "optional wine pairing from small Scottish importers.",
        start=at(-3, 19), hours=3.5, status=EventStatus.PUBLISHED,
        venue=("The Larder, 14 Grassmarket, Edinburgh EH1 2JU", 55.9474, -3.1966),
        tickets=[("Tasting menu", 85, 32, 2, None),
                 ("Tasting menu + wine pairing", 125, 16, 2, None)],
        sold_out=["Tasting menu + wine pairing"],
        orders=10,
        agenda=[(0, 30, "Welcome drink & snacks", None),
                (30, 150, "Seven courses", "Amara Nwosu"),
                (180, 30, "Cheese & digestifs", None)],
        questions=[("Dietary requirements", RegistrationFieldType.TEXTAREA, True,
                    ["None", "Vegetarian", "No shellfish", "Gluten free", "None — surprise me!"])],
        message=("Thank you for joining us",
                 "Thanks for making the Autumn Harvest dinner so special. The "
                 "menu and wine list are attached on our website — see you at "
                 "the winter supper."),
    ),
    dict(
        key="streetfood", calendar="food",
        title="Street Food Friday",
        description="Twenty traders, three bars and a DJ in a converted "
        "railway arch. Entry fee goes to the local food bank.",
        start=at(4, 17), hours=6, status=EventStatus.PUBLISHED,
        venue=("Kirkgate Market, George St, Leeds LS2 7HY", 53.7976, -1.5405),
        tickets=[("Entry", 5, 800, 8, "Food and drink paid on the day.")],
        orders=16,
    ),
    dict(
        key="wine", calendar="food",
        title="Natural Wine & Cheese Evening",
        description="Six low-intervention wines paired with British cheeses.",
        start=at(16, 19), hours=2.5, status=EventStatus.CANCELLED,
        venue=("Vinegar Yard, 72-82 St Thomas St, London SE1 3QU", 51.5037, -0.0835),
        tickets=[("Tasting", 40, 40, 2, None)],
        cancel_after_sales=4,
    ),
    # ---------------- comedy ----------------
    dict(
        key="openmic", calendar="comedy", organizer="jules",
        title="Open Mic Comedy Night",
        description="Ten new acts, five minutes each, one very forgiving "
        "audience. Hosted by Jules Okafor.",
        start=at(-35, 20), hours=2.5, status=EventStatus.PUBLISHED,
        venue=("The Caroline of Brunswick, 39 Ditchling Rd, Brighton BN1 4SB", 50.8313, -0.1352),
        tickets=[("Entry", 6, 70, 4, None)],
        orders=14,
    ),
    dict(
        key="latelaughs", calendar="comedy", organizer="jules",
        title="Late Laughs: Headliner Special",
        description="Three of the circuit's sharpest headliners plus a "
        "surprise guest. Strictly 18+.",
        start=at(9, 20), hours=2.5, status=EventStatus.PUBLISHED,
        venue=("The Stand, 333 Woodlands Rd, Glasgow G3 6NG", 55.8697, -4.2825),
        tickets=[("Standard", 18, 150, 4, None), ("Front row", 28, 12, 2, None)],
        low={"Standard": 4}, sold_out=["Front row"],
        orders=15,
        hosts=[("buyer2", HostRole.HOST)],
    ),
    # ---------------- sport ----------------
    dict(
        key="run10k", calendar="sport",
        title="Sunday 10K Social Run",
        description="An easy-paced 10K loop around Hyde Park, followed by "
        "coffee. All paces welcome — nobody gets left behind.",
        start=at(5, 9), hours=2, status=EventStatus.PUBLISHED,
        venue=("Hyde Park Corner, London W1J 7NT", 51.5027, -0.1527),
        tickets=[("Free place", 0, 60, 1, None)],
        orders=20,
        faq=[("Where do we meet?", "By the Wellington Arch, 10 minutes before the start."),
             ("Is there bag storage?", "No — travel light!")],
    ),
    dict(
        key="fiveaside", calendar="sport",
        title="Five-a-Side Charity Tournament",
        description="Sixteen teams, one trophy, all proceeds to Mind.",
        start=at(-14, 10), hours=7, status=EventStatus.PUBLISHED,
        venue=("Goals Birmingham, Aston Rd N, Birmingham B6 4DS", 52.4962, -1.8845),
        tickets=[("Player", 15, 80, 5, None), ("Spectator", 3, 150, 6, None)],
        orders=18,
        hosts=[("kofi", HostRole.MANAGER)],
    ),
    dict(
        key="climbing", calendar="sport",
        title="Climbing Taster Session",
        description="Ninety minutes on the bouldering wall with a coach. "
        "Shoes and chalk included.",
        start=at(40, 18), hours=1.5, status=EventStatus.PUBLISHED,
        venue=("The Foundry, 45 Mowbray St, Sheffield S3 8EN", 53.3920, -1.4718),
        tickets=[("Taster", 22, 24, 2, None)],
        orders=6,
        hosts=[("host", HostRole.MANAGER)],
    ),
    # ---------------- community ----------------
    dict(
        key="repaircafe", calendar="community",
        title="Neighbourhood Repair Café",
        description="Bring your broken toasters, torn jackets and wobbly "
        "chairs — volunteer fixers will help you mend them. Happening now!",
        start=NOW - timedelta(hours=1), hours=4, status=EventStatus.PUBLISHED,
        venue=("St Werburgh's Community Centre, Horley Rd, Bristol BS2 9TJ", 51.4679, -2.5723),
        tickets=[("Free entry", 0, 100, 2, None)],
        orders=18, checked_in_ratio=0.5,
        agenda=[(0, 120, "Repair tables open", None),
                (120, 60, "Sewing machine clinic", "Chloé Martin"),
                (180, 60, "Bike maintenance basics", "Liam O'Connell")],
        hosts=[("host", HostRole.HOST), ("chloe", HostRole.HOST)],
    ),
    dict(
        key="bookclub", calendar="community",
        title="Online Book Club: The Left Hand of Darkness",
        description="We're reading Ursula K. Le Guin's classic this month. "
        "Come having read it — or not; we won't tell.",
        start=at(12, 19), hours=1.5, status=EventStatus.PUBLISHED,
        venue="https://meet.google.com/lhd-book-club",
        tickets=[("Seat", 0, 50, 1, None)],
        orders=12,
        questions=[("Favourite book of the last year?", RegistrationFieldType.TEXT, False,
                    ["Piranesi", "Tomorrow, and Tomorrow, and Tomorrow",
                     "The Dispossessed", "Klara and the Sun"])],
    ),
    dict(
        key="garden", calendar="community",
        title="Community Garden Planting Day",
        description="Postponed due to flooding — we'll be back in spring.",
        start=at(-60, 10), hours=5, status=EventStatus.CANCELLED,
        venue=("Grow Wild Garden, Ashley Rd, Bristol BS6 5NP", 51.4720, -2.5824),
        tickets=[("Volunteer spot", 0, 40, 2, None)],
    ),
]

# Hand-picked purchases so the login accounts have something to look at:
# (buyer, event, [(ticket type, qty)], state, check_in)
# state: paid | pending | cancelled. check_in: list of per-ticket flags for
# past events (True = used), or None to leave tickets valid.
SCRIPTED_ORDERS = [
    ("buyer", "midnight", [("General Admission", 2)], "paid", [True, False]),
    ("buyer", "vuemeetup", [("Free RSVP", 1)], "paid", [True]),
    ("buyer", "tasting", [("Tasting menu", 2)], "paid", [True, True]),
    ("buyer", "jazz", [("VIP Table", 2)], "paid", None),
    ("buyer", "aisummit", [("Early Bird", 1)], "paid", None),
    ("buyer", "streetfood", [("Entry", 3)], "paid", None),
    ("buyer", "indie", [("General Admission", 2)], "pending", None),
    ("buyer", "climbing", [("Taster", 1)], "cancelled", None),
    ("buyer2", "midnight", [("VIP", 1)], "paid", [False]),
    ("buyer2", "openmic", [("Entry", 2)], "paid", [True, True]),
    ("buyer2", "run10k", [("Free place", 1)], "paid", None),
    ("buyer2", "bookclub", [("Seat", 1)], "paid", None),
    ("buyer2", "postgres", [("Live + recording", 1)], "pending", None),
    ("host", "aisummit", [("General Admission", 1)], "paid", None),
]
# (buyer, event): cancel one ticket of this paid order after issue (a refund).
PARTIAL_CANCELS = [("buyer", "streetfood")]


# --------------------------------------------------------------------------
# Reset / detection
# --------------------------------------------------------------------------


def demo_calendar_ids(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(Calendar.id).where(Calendar.slug.in_(DEMO_CALENDAR_SLUGS))
        ).all()
    )


def reset(db: Session) -> None:
    """Delete every demo row. Login accounts and non-demo data are kept."""
    cal_ids = demo_calendar_ids(db)
    event_ids = list(
        db.scalars(select(Event.id).where(Event.calendar_id.in_(cal_ids))).all()
    )
    order_ids = list(
        db.scalars(
            select(OrderItem.order_id)
            .join(TicketType, TicketType.id == OrderItem.ticket_type_id)
            .where(TicketType.event_id.in_(event_ids))
            .distinct()
        ).all()
    )
    # Orders hang off users, not events, so remove them explicitly first.
    db.execute(delete(Order).where(Order.id.in_(order_ids)))
    db.execute(
        delete(Notification).where(
            Notification.calendar_id.in_(cal_ids)
            | Notification.event_id.in_(event_ids)
        )
    )
    # Cascades to events, ticket types, tickets, hosts, agenda, FAQ, messages…
    db.execute(delete(Calendar).where(Calendar.id.in_(cal_ids)))
    db.execute(delete(User).where(User.email.like(f"%@{DEMO_DOMAIN}")))
    db.commit()
    print(
        f"Reset: removed {len(cal_ids)} calendars, {len(event_ids)} events, "
        f"{len(order_ids)} orders and demo users."
    )


# --------------------------------------------------------------------------
# Seeding
# --------------------------------------------------------------------------


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    hashed = hash_password(PASSWORD)
    for key, email, name, role in LOGINS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=name)
            db.add(user)
        user.hashed_password = hashed
        user.role = role
        user.is_active = True
        user.full_name = user.full_name or name
        users[key] = user
    for key, name, role in DEMO_PEOPLE:
        user = User(
            email=f"{key}@{DEMO_DOMAIN}",
            full_name=name,
            hashed_password=hashed,
            role=role,
        )
        db.add(user)
        users[key] = user
    db.commit()
    return users


def seed_calendars(db: Session, users: dict[str, User]) -> dict[str, Calendar]:
    calendars: dict[str, Calendar] = {}
    for key, slug, name, owner, description, followers in CALENDARS:
        cal = Calendar(
            name=name,
            slug=slug,
            description=description,
            image_url=img(f"cal-{key}"),
            is_public=True,
            owner_id=users[owner].id,
        )
        db.add(cal)
        db.flush()
        db.add_all(
            CalendarFollower(calendar_id=cal.id, user_id=users[f].id)
            for f in followers
        )
        calendars[key] = cal
    db.commit()
    return calendars


def seed_events(
    db: Session, users: dict[str, User], calendars: dict[str, Calendar]
) -> dict[str, Event]:
    events: dict[str, Event] = {}
    for spec in EVENTS:
        venue = spec["venue"]
        if isinstance(venue, str):
            location, lat, lng = validate_location(
                is_online=True, location=venue, lat=None, lng=None
            )
        else:
            location, lat, lng = validate_location(
                is_online=False, location=venue[0], lat=venue[1], lng=venue[2]
            )
        start: datetime = spec["start"]
        event = Event(
            title=spec["title"],
            description=spec["description"],
            start_datetime=start,
            end_datetime=start + timedelta(hours=spec["hours"]),
            location=location,
            is_online=isinstance(venue, str),
            lat=lat,
            lng=lng,
            image_url=img(spec["key"]),
            capacity=sum(t[2] for t in spec["tickets"]),
            status=spec["status"],
            organizer_id=users[spec.get("organizer", "organizer")].id,
            calendar_id=calendars[spec["calendar"]].id,
        )
        for name, price, qty, max_per, desc in spec["tickets"]:
            event.ticket_types.append(
                TicketType(
                    name=name,
                    description=desc,
                    price=price,
                    quantity_available=qty,
                    max_per_order=max_per,
                )
            )
        for i, (offset, minutes, title, speaker) in enumerate(spec.get("agenda", [])):
            item_start = start + timedelta(minutes=offset)
            event.agenda_items.append(
                AgendaItem(
                    start_time=item_start,
                    end_time=item_start + timedelta(minutes=minutes),
                    title=title,
                    speaker_name=speaker,
                    sort_order=i,
                )
            )
        for i, (question, answer) in enumerate(spec.get("faq", [])):
            event.faq_items.append(
                EventFaqItem(question=question, answer=answer, sort_order=i)
            )
        for i, (label, field_type, required, _) in enumerate(spec.get("questions", [])):
            event.registration_questions.append(
                RegistrationQuestion(
                    label=label, field_type=field_type, required=required, sort_order=i
                )
            )
        for user_key, role in spec.get("hosts", []):
            host = users[user_key]
            event.hosts.append(
                EventHost(
                    email=host.email,
                    name=host.full_name,
                    role=role,
                    user_id=host.id,
                    status=HostStatus.ACCEPTED,
                    show_on_page=True,
                )
            )
        if pending := spec.get("pending_host"):
            event.hosts.append(
                EventHost(
                    email=pending[0],
                    name=pending[1],
                    role=HostRole.HOST,
                    status=HostStatus.PENDING,
                    show_on_page=False,
                )
            )
        db.add(event)
        events[spec["key"]] = event
    db.commit()
    return events


def _answers(event: Event, spec: dict) -> list[RegistrationAnswerInput]:
    """Plausible registration answers: all required, most optional."""
    samples = {label: options for label, _, _, options in spec.get("questions", [])}
    return [
        RegistrationAnswerInput(question_id=q.id, value=rng.choice(samples[q.label]))
        for q in event.registration_questions
        if q.required or rng.random() < 0.7
    ]


def _backdate(order: Order, event: Event) -> None:
    """Orders placed some days before the event (or before now, if later)."""
    anchor = min(event.start_datetime, NOW)
    placed = anchor - timedelta(days=rng.randint(1, 25), hours=rng.randint(0, 23))
    order.created_at = placed
    for ticket in order.tickets:
        ticket.created_at = placed


def place_order(
    db: Session,
    buyer: User,
    event: Event,
    spec: dict,
    lines: list[tuple[str, int]],
    state: str,
) -> Order:
    by_name = {tt.name: tt for tt in event.ticket_types}
    order = crud.order.create(
        db,
        obj_in=OrderCreate(
            items=[
                OrderItemCreate(ticket_type_id=by_name[name].id, quantity=qty)
                for name, qty in lines
            ],
            answers=_answers(event, spec),
        ),
        user_id=buyer.id,
    )
    if state == "paid":
        # Issues tickets with codes exactly as the Stripe webhook does.
        order = crud.order.fulfill(db, order_id=order.id)
    elif state == "cancelled":
        order = crud.order.release(db, order_id=order.id)
    _backdate(order, event)
    db.commit()
    return order


def check_in(ticket: Ticket, event: Event) -> None:
    ticket.status = TicketStatus.USED
    ticket.checked_in_at = event.start_datetime + timedelta(
        minutes=rng.randint(0, 90)
    )


def seed_orders(
    db: Session, users: dict[str, User], events: dict[str, Event]
) -> None:
    specs = {s["key"]: s for s in EVENTS}
    customers = [
        u for u in users.values()
        if u.role is UserRole.CUSTOMER and u.email != users["host"].email
    ]

    # Scripted orders for the login accounts.
    scripted: dict[tuple[str, str], Order] = {}
    for buyer, key, lines, state, flags in SCRIPTED_ORDERS:
        order = place_order(db, users[buyer], events[key], specs[key], lines, state)
        scripted[(buyer, key)] = order
        if flags:
            for ticket, used in zip(order.tickets, flags):
                if used:
                    check_in(ticket, events[key])
    for buyer, key in PARTIAL_CANCELS:
        scripted[(buyer, key)].tickets[-1].status = TicketStatus.CANCELLED
    db.commit()

    # Random crowd for every on-sale event.
    for key, event in events.items():
        spec = specs[key]
        if event.status is EventStatus.DRAFT:
            continue
        n_orders = spec.get("orders", spec.get("cancel_after_sales", 0))
        is_past = event.start_datetime < NOW
        for i in range(n_orders):
            in_stock = [tt for tt in event.ticket_types if tt.quantity_available > 0]
            if not in_stock:
                break
            tt = rng.choice(in_stock)
            qty = rng.randint(1, min(3, tt.max_per_order, tt.quantity_available))
            # Upcoming events get the occasional abandoned/expired checkout.
            roll = rng.random()
            state = (
                "pending" if not is_past and roll < 0.08
                else "cancelled" if roll > 0.94
                else "paid"
            )
            order = place_order(
                db, rng.choice(customers), event, spec, [(tt.name, qty)], state
            )
            if state != "paid":
                continue
            if is_past:
                ratio = spec.get("checked_in_ratio", 0.7)
                for ticket in order.tickets:
                    if rng.random() < ratio:
                        check_in(ticket, event)
            elif qty > 1 and i % 5 == 0:
                order.tickets[-1].status = TicketStatus.CANCELLED  # refunded one
        db.commit()

        # Cancelled event: every issued ticket is void.
        if event.status is EventStatus.CANCELLED:
            for ticket in db.scalars(
                select(Ticket).join(Ticket.ticket_type).where(TicketType.event_id == event.id)
            ):
                ticket.status = TicketStatus.CANCELLED

        # Force the stock levels the spec asks for.
        for tt in event.ticket_types:
            if tt.name in spec.get("sold_out", []):
                tt.quantity_available = 0
            elif tt.name in spec.get("low", {}):
                tt.quantity_available = spec["low"][tt.name]
        db.commit()


def seed_messages_and_notifications(
    db: Session, users: dict[str, User], events: dict[str, Event]
) -> None:
    specs = {s["key"]: s for s in EVENTS}
    for key, event in events.items():
        if msg := specs[key].get("message"):
            recipients = crud.order.get_event_recipient_emails(db, event_id=event.id)
            db.add(
                EventMessage(
                    event_id=event.id,
                    sent_by_id=event.organizer_id,
                    subject=msg[0],
                    body=msg[1],
                    recipient_count=len(recipients),
                    created_at=min(NOW, event.start_datetime) - timedelta(hours=20),
                )
            )
    db.commit()

    # Same fan-out the app does on publish (emails aren't sent from here).
    for event in events.values():
        if event.status is EventStatus.PUBLISHED:
            crud.notification.notify_new_event(db, event=event)
    # Backdate them to roughly when each event went on sale; older ones read.
    for note in db.scalars(
        select(Notification).where(Notification.event_id.in_([e.id for e in events.values()]))
    ):
        event = next(e for e in events.values() if e.id == note.event_id)
        note.created_at = min(NOW, event.start_datetime) - timedelta(days=rng.randint(10, 30))
        note.is_read = event.start_datetime < NOW or rng.random() < 0.3
    db.commit()


def summary(db: Session) -> None:
    cal_ids = demo_calendar_ids(db)
    event_ids = select(Event.id).where(Event.calendar_id.in_(cal_ids))
    tickets = select(Ticket).join(Ticket.ticket_type).where(TicketType.event_id.in_(event_ids))
    order_ids = (
        select(OrderItem.order_id)
        .join(TicketType, TicketType.id == OrderItem.ticket_type_id)
        .where(TicketType.event_id.in_(event_ids))
    )

    def count(stmt) -> int:
        return db.scalar(select(func.count()).select_from(stmt.subquery()))

    demo_users = count(select(User).where(User.email.like(f"%@{DEMO_DOMAIN}")))
    print("\nDemo data summary")
    print(f"  users:       {demo_users + len(LOGINS)} ({len(LOGINS)} logins + {demo_users} demo)")
    print(f"  calendars:   {len(cal_ids)}")
    print(f"  events:      {count(select(Event).where(Event.calendar_id.in_(cal_ids)))}")
    orders = select(Order).where(Order.id.in_(order_ids))
    by_status = ", ".join(
        f"{s.value} {count(orders.where(Order.status == s))}" for s in OrderStatus
    )
    print(f"  orders:      {count(orders)} ({by_status})")
    print(f"  tickets:     {count(tickets)} ({count(tickets.where(Ticket.status == TicketStatus.CANCELLED))} cancelled)")
    print(f"  checked in:  {count(tickets.where(Ticket.status == TicketStatus.USED))}")
    print(f"\nLog in with any of these (password '{PASSWORD}'):")
    for _, email, _, role in LOGINS:
        print(f"  {email:28} {role.value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local demo data.")
    parser.add_argument(
        "--reset", action="store_true",
        help="delete previously generated demo rows first, then reseed",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if args.reset:
            reset(db)
        elif demo_calendar_ids(db):
            print("Demo data already present — nothing to do. Use --reset to regenerate.")
            summary(db)
            return

        users = seed_users(db)
        calendars = seed_calendars(db, users)
        events = seed_events(db, users, calendars)
        seed_orders(db, users, events)
        seed_messages_and_notifications(db, users, events)
        summary(db)


if __name__ == "__main__":
    main()
