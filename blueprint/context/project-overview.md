# Ren - Project Overview

<!-- blueprint:source-hash a11c043e54eef0b04a39872668d5f7b46bc3857dca8ab8a47cfd5fbbad634d41 -->

> Event ticketing for independent organizers and communities: run calendars of
> events, sell tickets through Stripe, and check guests in by QR code.

## Problem

Independent organizers and communities need a simple way to publish events, sell
tickets, and run the door without the cost and complexity of large ticketing
platforms. Attendees need one place to discover events, buy tickets, and keep
track of the tickets they hold.

## Users

- **Attendees** (`customer`, default role) - discover events, buy tickets, follow
  calendars, present a QR ticket at the door. Browsing is anonymous; buying,
  following, and My Tickets need sign-in.
- **Organizers** (`organizer`) - own calendars and events, sell tickets, manage
  guests, message guests, check guests in. Co-hosts can be added per event.
- **Admins** (`admin`) - platform operators. The role bypasses ownership checks
  in the API but has no UI yet (Feature 16).

## Usage model

- Internet-facing: public event pages and real payments via Stripe.
- Real trust boundaries: auth and roles; event ownership and co-host (manager)
  permissions; Stripe webhook signature verification; file uploads; ticket
  check-in codes.

## Features

Build-plan order. 1-15 are shipped; 16 is next.

1. ✅ **Auth and users** - email/password register/login, JWT, three roles.
2. ✅ **Events** - organizer CRUD with draft/published/cancelled status, public listing and detail.
3. ✅ **Ticket types** - priced tiers per event with quantity and max per order.
4. ✅ **Orders** - order creation with inventory reservation; My Orders.
5. ✅ **Stripe payments** - Checkout Session plus webhook fulfilment that issues tickets. *(Headline: paid ticketing.)*
6. ✅ **Guest event views** - public event pages and booking UI.
7. ✅ **Organizer dashboard** - manage events, ticket types, guests, hosts, questions, messages.
8. ✅ **Calendars** - organizer calendars with slug pages, followers, new-event notifications.
9. ✅ **Event agendas and FAQ** - agenda items and reorderable FAQ per event.
10. ✅ **Notifications** - in-app bell and list; follower emails.
11. ✅ **User profiles** - profile editing, avatars, public profile pages.
12. ✅ **Event images** - upload and remove cover images.
13. ✅ **Geocoded locations** - Places Autocomplete on the form, map embed on the event page.
14. ✅ **Event search** - search input on the events listing.
15. ✅ **QR tickets and check-in** - per-ticket codes, QR in My Tickets, door scan with stats.
16. **Admin area** - UI for admins to manage users, roles, and events.
17. **Organizer analytics** - sales, revenue, and attendance reporting on the dashboard.
18. **Ticket emails** - order confirmation email with QR tickets after payment.
19. **Refunds and cancellations** - Stripe refunds for paid orders; event cancellation handling for ticket holders.
20. **Forgot password** - password reset via email.
21. **Discount codes** - organizer promo codes that reduce ticket price at checkout.
22. **Waitlist** - join a waitlist when an event or ticket type is sold out.
23. **Payouts** - organizer payout tracking and status (or Stripe Connect onboarding).
24. **Invoices** - downloadable invoices/receipts for completed orders.
25. **Event privacy** - private/unlisted (link-only or invite-only) vs public events.
26. **Categories and tags** - tag events so search and discovery can filter by category.
27. **Profile social links** - website and social links on profiles.
28. **Add-ons** - optional purchasable extras attached to an event or order.
29. **Invitations** - invite specific people to an event by email or link.
30. **Message templates** - reusable templates for organizer-to-guest emails.

## Data model

SQLAlchemy 2.0 models in `backend/app/models/`. All tables have integer `id`;
most have `created_at`/`updated_at` (timestamptz). FKs cascade on delete unless
noted. These shapes are shipped and locked; later features extend them through
idempotent scripts in `backend/scripts/`.

### User (`users`)

- `email` (str, unique), `hashed_password` (str), `full_name`, `display_name` (str?)
- `role` (enum `customer` | `organizer` | `admin`, default `customer`)
- `is_active` (bool, default true), `bio` (text?), `avatar_url` (str?)
- has many calendars, events (as organizer), orders, tickets, calendar follows, notifications

### Calendar (`calendars`) / CalendarFollower (`calendar_followers`)

- Calendar: `name`, `slug` (unique), `description?`, `image_url?`, `is_public` (bool), `owner_id` -> User; has many events
- CalendarFollower: `calendar_id`, `user_id`; unique (`calendar_id`, `user_id`)

### Event (`events`)

- `title`, `description?`, `start_datetime`, `end_datetime` (timestamptz)
- `location?` (str), `is_online` (bool), `lat`/`lng` (float?), `image_url?`, `capacity?` (int)
- `status` (enum `draft` | `published` | `cancelled`)
- `organizer_id` -> User, `calendar_id` -> Calendar
- has many ticket types, agenda items, FAQ items, messages, registration questions, hosts

### EventHost (`event_hosts`)

- `event_id`, `user_id?` -> User (SET NULL), `email`, `name?`
- `role` (enum `manager` - can manage the event once linked | `host` - display only)
- `status` (enum `pending` - invited by email | `accepted` - linked to an account), `show_on_page` (bool)
- unique (`event_id`, `email`)

### TicketType (`ticket_types`)

- `event_id`, `name`, `description?`, `price` (numeric 10,2), `quantity_available` (int), `max_per_order` (int)

### Order (`orders`) / OrderItem (`order_items`)

- Order: `user_id`, `status` (enum `pending` -> `paid` | `cancelled`), `total_amount` (numeric),
  `stripe_session_id` (unique?), `stripe_payment_intent_id?`
- Lifecycle: created `pending` with inventory reserved; `paid` on Stripe webhook (tickets issued);
  `cancelled` on session expiry/failure (inventory released)
- OrderItem: `order_id`, `ticket_type_id`, `quantity`, `unit_price` (numeric 10,2)

### Ticket (`tickets`)

- `order_id`, `ticket_type_id`, `owner_id` -> User
- `status` (enum `valid` | `used` | `cancelled`), `code` (str, unique, check-in QR payload), `checked_in_at?`

### Event content

- AgendaItem (`agenda_items`): `event_id`, `start_time`, `end_time?`, `title`, `description?`, `speaker_name?`, `location?`, `sort_order`
- EventFaqItem (`event_faq_items`): `event_id`, `question`, `answer`, `sort_order`
- RegistrationQuestion (`registration_questions`): `event_id`, `label`, `field_type` (enum `text` | `textarea` | `url`), `required`, `sort_order`
- RegistrationAnswer (`registration_answers`): `order_id`, `question_id`, `value`; unique (`order_id`, `question_id`)

### Messaging

- EventMessage (`event_messages`): `event_id`, `sent_by_id` -> User (SET NULL), `subject`, `body`, `recipient_count`
- Notification (`notifications`): `user_id`, `type` (enum `event_published`), `title`, `message?`,
  `event_id?`/`calendar_id?` (SET NULL), `is_read`

### Files

- Avatars and event images on local disk under `backend/uploads/`; models store the URL.

## Tech stack

- **Python 3.12 + FastAPI** - REST API under `/api/v1`, docs at `/docs`
- **SQLAlchemy 2.0 (`Mapped`) + Pydantic v2 + pydantic-settings** - models, schemas, config
- **PostgreSQL 16** - tables via `Base.metadata.create_all` on startup; column changes as idempotent scripts in `backend/scripts/`
- **JWT (python-jose) + passlib/bcrypt** - auth; token in browser localStorage
- **Stripe Checkout + webhook** - payments and ticket fulfilment
- **SMTP via `smtplib`** - email, console logging fallback in dev
- **Google Maps Places Autocomplete + Maps Embed** - location entry and display (browser key)
- **Nuxt 4 (Vue 3, TypeScript) + `@nuxtjs/tailwindcss` (Tailwind v3) + Boxicons** - frontend
- **`qrcode` / `jsqr`** - render ticket QR codes, scan at the door
- **Docker Compose** - db, backend, frontend with hot reload

## Monetization

> TODO: not decided. Plan lists per-ticket platform fee or organizer subscription as options.

## UI/UX

Clean, card-based Tailwind UI, purple accent (`purple-600`), Boxicons, persisted
light/dark toggle. Public pages focus on discovery and booking; organizer tools
live under `/dashboard`.

- `/` - home; `/events`, `/events/[id]` - discovery, search, event detail and booking
- `/calendar/[slug]` - public calendar page with follow
- `/users/[id]` - public profile; `/account` - edit profile
- `/login`, `/register`
- `/my-tickets` - tickets with QR codes; `/notifications` - notification list
- `/dashboard` - organizer home; `/dashboard/calendars` (+ `new`, `[id]`)
- `/dashboard/events/new`, `/dashboard/events/[id]` - event management; `/dashboard/events/[id]/check-in` - QR door scan

> TODO: reference products or design goals not yet stated.

## Deployment

> TODO: no production target chosen. Known needs:

- Backend: `uvicorn app.main:app`; health check `GET /health`
- Frontend: `nuxt build` then `node .output/server/index.mjs` (or `nuxt generate`)
- PostgreSQL plus persistent storage for `backend/uploads/`
- Env vars: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
  `FRONTEND_URL`, `BACKEND_CORS_ORIGINS`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`,
  `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY`, `EMAIL_ENABLED`, `SMTP_*`, `EMAILS_FROM_*`,
  `NUXT_PUBLIC_API_BASE`, `NUXT_PUBLIC_GOOGLE_MAPS_API_KEY`

## Open questions

- **Roadmap order** - build plan marks the order of 16-19 as a guess, and 20-30 were appended after it. Confirm the order.
- **Plan drift** - project-plan §3 "Next" lists only 16-19; features 20-30 (forgot password, discount codes, waitlist, payouts, invoices, privacy, tags, social links, add-ons, invitations, templates) appear only in the build plan.
- **Payouts (23)** - "tracking" vs Stripe Connect onboarding is undecided; this changes architecture and money flow.
- **Data for upcoming features** - project-plan §4 has no data for refunds, discount codes, waitlist, payouts, invoices, privacy, tags, social links, add-ons, invitations, or templates. Each `/feature` spec will need to define it.
- **Invitations vs co-hosts** - Feature 29 invitations overlap with existing email-based host invites and Feature 25 invite-only privacy; boundaries need defining.
- **Unconfirmed TODOs** in project-plan: problem statement (§1), monetization (§6), design references (§7), deployment target (§8).
- **Admin role** - API bypasses ownership for admins with no UI yet; Feature 16 should confirm which admin powers are intended.
