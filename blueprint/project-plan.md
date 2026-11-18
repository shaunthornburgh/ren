# Project Plan

> Seeded by `/adopt` from the existing codebase plus a short interview. Items
> marked `> TODO (confirm)` are inferences; correct them before `/overview`.

## 1. Problem - What problem are we solving?

Independent organizers and communities need a simple way to publish events, sell
tickets, and run the door, without the cost and complexity of large ticketing
platforms. Attendees need one place to discover events, buy tickets, and keep
track of the ones they hold.

> TODO (confirm): problem statement inferred from the code and "independent
> organizers" answer. Add anything specific (fees, UX, community focus).

## 2. Users - Who is this for?

- **Organizers** (role `organizer`) - independent organizers and communities who
  run calendars of events, sell tickets, and check guests in.
- **Attendees** (role `customer`, the default) - people who discover events, buy
  tickets, follow calendars, and present a QR ticket at the door.
- **Admins** (role `admin`) - platform operators. The role exists and bypasses
  ownership checks in the API, but has no dedicated UI yet.

## 3. Features - What does the MVP need?

Already shipped:

- Email/password registration and login with JWT and roles
- User profiles with avatars and public profile pages
- Calendars (organizer-owned collections of events) with public slug pages and followers
- Events with draft/published/cancelled status, images, geocoded location and map
- Event search and discovery
- Ticket types (price, quantity, max per order)
- Orders with inventory reservation and Stripe Checkout payment (webhook fulfilment)
- My Tickets with QR codes
- Organizer dashboard for calendars and events
- Event agenda, FAQ, registration questions, and co-hosts (manager/host roles)
- Guest list with registration answers
- Organizer messages to guests (email)
- In-app notifications and email to calendar followers on new events
- Door check-in by QR scan, with stats
- Light/dark theme

Next (see `build-plan.md`): admin area, organizer analytics, ticket emails,
refunds and cancellations.

## 4. Data - What are we storing?

PostgreSQL via SQLAlchemy models in `backend/app/models/`:

- `users` (email, hashed password, role, profile, avatar)
- `calendars`, `calendar_followers`
- `events` (status, schedule, location and coordinates, image, capacity)
- `ticket_types`, `orders`, `order_items`, `tickets` (unique check-in `code`, `checked_in_at`)
- `agenda_items`, `faq_items`, `registration_questions` and answers
- `event_hosts`, `event_messages`, `notifications`
- Uploaded files (avatars, event images) on local disk under `backend/uploads/`

## 5. Tech - What stack are we using?

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (`Mapped` declarative), Pydantic v2, pydantic-settings
- **Database:** PostgreSQL 16. Tables created by `Base.metadata.create_all` on startup; column changes ship as idempotent one-off scripts in `backend/scripts/`
- **Auth:** JWT (python-jose) with passlib/bcrypt; token stored in browser localStorage
- **Payments:** Stripe Checkout + webhook
- **Email:** SMTP via stdlib `smtplib`, console logging fallback in dev
- **Maps:** Google Maps Places Autocomplete and Maps Embed (browser key)
- **Frontend:** Nuxt 4 (Vue 3, TypeScript), `@nuxtjs/tailwindcss` (Tailwind v3), Boxicons, `qrcode` and `jsqr` for tickets and scanning
- **Dev environment:** Docker Compose (db, backend, frontend) with hot reload

The user confirmed this stack and structure are intentional.

## 6. Monetize - How will this make money?

> TODO (confirm): not established. Options include a per-ticket platform fee or
> organizer subscription. Leave blank if not decided.

## 7. UI/UX - How should this look and feel?

Clean, card-based Tailwind UI with a purple accent (`purple-600`), Boxicons
icons, and a persisted light/dark theme toggle. Public pages focus on discovery
and booking; organizer tools live under `/dashboard`.

> TODO (confirm): add any reference products or design goals.

## 8. Deployment - Where and how will this ship?

> TODO (confirm): no production target found in the repo. Known needs:
> - Backend: `uvicorn app.main:app`, health check `GET /health`
> - Frontend: `nuxt build` then `node .output/server/index.mjs` (or `nuxt generate`)
> - PostgreSQL, persistent storage for `uploads/`
> - Env vars: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
>   `FRONTEND_URL`, `BACKEND_CORS_ORIGINS`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`,
>   `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY`, `EMAIL_ENABLED`, `SMTP_*`, `EMAILS_FROM_*`,
>   `NUXT_PUBLIC_API_BASE`, `NUXT_PUBLIC_GOOGLE_MAPS_API_KEY`

## 9. Usage model and constraints (optional)

- Internet-facing: public event pages, real payments via Stripe.
- Real trust boundaries: auth and roles, event ownership and co-host permissions,
  Stripe webhook signature verification, file uploads, ticket check-in codes.
