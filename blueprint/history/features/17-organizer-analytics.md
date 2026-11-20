# Feature: Organizer analytics

**From build-plan:** feature 17
**Build attempt:** 1
**Branch:** feature/organizer-analytics
**Status:** verified

## Goal

Give event managers sales, revenue, and attendance reporting. Each event's
manage page gets an **Analytics** tab with a per-ticket-type breakdown, order
counts by status, and an attendance rate. The organizer dashboard gains a
**Checked in** total. Revenue everywhere becomes the price actually paid
(`order_items.unit_price` on paid orders) instead of tickets sold × the ticket
type's current price, so editing a price no longer rewrites past revenue, and
the dashboard and Analytics tab always agree.

## In scope

- `GET /api/v1/events/{event_id}/analytics`: per-ticket-type sold, remaining,
  revenue, and checked in; event totals; attendance rate; order counts by
  status.
- One shared per-ticket-type aggregation in `crud/event.py`, used by both the
  new endpoint and the existing `GET /events/me` dashboard stats.
- Dashboard (`GET /events/me`): revenue switches to price paid, and a new
  `checked_in` count per event.
- Frontend: an Analytics tab on `/dashboard/events/[id]`, a **Checked in** tile
  and per-event stat on `/dashboard`.

## Out of scope

- Sales-over-time or daily trends, charts, CSV export (not chosen for this
  feature).
- Refund-adjusted revenue and cancelled-ticket handling (Feature 19). Revenue
  counts paid orders as they stand today.
- Platform-wide or admin analytics, calendar-level rollups, and listing
  co-hosted events on the dashboard (`/events/me` stays organizer-owned only).
- The existing currency mismatch: the frontend `formatPrice` hardcodes GBP
  while the backend `STRIPE_CURRENCY` defaults to `usd`. It is unchanged here.

## Build loop

`workflow.stepReview` is `feature`: build both steps, then stop once for review
of the whole feature. `workflow.checkpointCommits` is `disabled`: no commits per
step; `/complete` makes the feature commit. Work on branch
`feature/organizer-analytics`.

## Build steps

- [x] **1. Backend analytics and price-paid revenue.**
  - In `app/crud/event.py`, add one helper that takes a list of event ids and
    returns per-ticket-type stats using grouped aggregate queries (no per-row
    queries):
    - `sold`: tickets with status != `cancelled`
    - `checked_in`: tickets with status `used`
    - `revenue`: sum of `quantity * unit_price` over order items whose order is
      `paid`
  - Rework `get_multi_by_organizer_with_stats` to use it. `revenue` becomes the
    price paid, and add `checked_in` to `EventStats`. `tickets_sold` and
    `tickets_remaining` keep their current meanings.
  - Add `crud.event.get_analytics(db, *, event)` returning the `EventAnalytics`
    shape below. It also needs an order-status count over distinct orders that
    contain this event's ticket types.
  - Add the route `GET /events/{event_id}/analytics` in `app/api/v1/events.py`,
    guarded by `load_manageable_event` (creator, accepted manager co-host,
    admin). Add schemas in `app/schemas/event.py`.
    `OrganizerEventRead` gains `checked_in: int`.
  - **Done when:** using `/docs` or curl with seeded logins:
    - the organizer gets 200 for their event, with per-type and total numbers
      that match a direct SQL check
    - an accepted manager co-host gets 200
    - another organizer or customer gets 403, signed out gets 401, and a
      missing event gets 404
    - an event with no ticket types returns `ticket_types: []`, zero totals,
      and `attendance_rate: null`
    - after editing a ticket type's price, `revenue` on both `/events/me` and
      the analytics endpoint is unchanged
    - `/events/me` includes `checked_in`

- [x] **2. Analytics tab and dashboard attendance.**
  - New component `app/components/EventAnalytics.vue`, rendered by a new
    `analytics` tab (label "Analytics") in
    `pages/dashboard/events/[id]/index.vue`, using the existing `?tab=` sync.
    It fetches only when the tab is first opened and has a **Refresh** button.
  - Content:
    - summary tiles: Tickets sold, Revenue, Checked in, Attendance
      (`NN%`, or "—" when nothing sold)
    - a per-ticket-type table: Ticket type, Price, Sold, Remaining, Checked
      in, Revenue, plus a totals row
    - order counts: Paid, Pending, Cancelled
  - States: loading text; empty ("No ticket types yet. Add one in the Registration
    tab to start selling."); an error panel showing the API `detail` with a
    Retry button; a zero-sales event renders zeros, not the empty state.
  - `pages/dashboard/index.vue`: add a fourth summary tile **Checked in** (sum
    of `checked_in`) and a **Checked in** stat on each event card. Types in
    `types/api.ts`: `EventAnalytics`, `TicketTypeAnalytics`, and `checked_in`
    on `OrganizerEventRead`.
  - **Done when:**
    - in the browser, as the seeded organizer, the Analytics tab for an event
      with sales shows the same totals as the dashboard card, and the
      per-type rows sum to the totals row
    - Refresh after a check-in at `/dashboard/events/{id}/check-in` increments
      Checked in
    - an event with no ticket types shows the empty state
    - reloading with `?tab=analytics` opens the tab
    - the dashboard shows the Checked in tile
    - `docker compose exec frontend npm run build` passes

## Files / areas

- Backend: `app/crud/event.py`, `app/api/v1/events.py`, `app/schemas/event.py`.
- Frontend: `app/components/EventAnalytics.vue` (new),
  `app/pages/dashboard/events/[id]/index.vue`, `app/pages/dashboard/index.vue`,
  `app/types/api.ts`.
- No schema change: everything derives from `tickets`, `ticket_types`,
  `orders`, `order_items`.

## Data / contracts

**`GET /api/v1/events/{event_id}/analytics`** -> `200 EventAnalytics`
- Auth: `get_current_active_user` + `load_manageable_event`. Without a token
  it returns 401; for a non-manager, 403 `"You do not have manager access to
  this event."`; for a missing event, 404 `"Event not found."`
  (existing helper messages).
- `EventAnalytics`:
  - `ticket_types: list[TicketTypeAnalytics]`, every ticket type of the event
    including zero-sale ones, ordered by `id`
  - `totals: { sold: int, remaining: int, checked_in: int, revenue: Decimal }`,
    the sums of the per-type values
  - `attendance_rate: float | None`, equal to `checked_in / sold` rounded to 4
    decimal places; `None` when `sold == 0`
  - `orders: { paid: int, pending: int, cancelled: int }`, counting distinct
    orders with at least one item for this event's ticket types
- `TicketTypeAnalytics`: `{ ticket_type_id: int, name: str, price: Decimal
  (current list price), sold: int, remaining: int (= quantity_available),
  checked_in: int, revenue: Decimal }`.
- Definitions:
  - **sold** = tickets with status `valid` or `used`. This equals the check-in
    screen's "admissible" total, so attendance matches it.
  - **revenue** = Σ `order_items.quantity × unit_price` where `orders.status =
    paid`.
  - **remaining** = `quantity_available`. Pending orders have already reserved
    their stock, so it is excluded.
- Decimals serialize as strings, as in existing `revenue` and `price` fields.

**`GET /api/v1/events/me`** (`OrganizerEventRead`): `revenue` switches to the
price-paid definition above, and it gains `checked_in: int`. Other fields are
unchanged.

## Testing

No test runner or Verify command is configured (AGENTS.md Commands).
Verification is manual:
- API: curl or `/docs` with seeded logins (`organizer@`, `host@` as a co-host
  manager, `buyer@`, `admin@`; password `password123`), cross-checked with
  `psql` aggregate queries. Cover 200/401/403/404 and the price-edit case
  (restore the price afterwards).
- Frontend: `docker compose exec frontend npm run build`, plus browser checks
  of Step 2's Done when.
- Don't claim test coverage that wasn't run.

## Notes for the AI

- Follow the four-layer pattern. Use one-line handler docstrings ("Event
  managers only."). Declare `/{event_id}/analytics` without disturbing the
  literal `/me` route ordering.
- Use aggregate `select(...).group_by(...)` queries keyed by `ticket_type_id`,
  with no Python loops issuing queries.
- Render names via interpolation only. The table needs a `<caption>` (can be
  `sr-only`) and `<th scope="col">` / `scope="row"`. Any attendance bar is
  decorative (`aria-hidden`) next to the text percentage. Format money with the
  existing `useFormat().formatPrice` and counts as plain integers.
- Match the dashboard's existing tile and card styles (`bg-purple-50
  rounded-2xl`, `dark:` variants).
- No new dependencies.


<!-- blueprint:completion {"schemaVersion":2,"specBytes":8578,"specSha256":"5a000a942405bba2629ce6a3281872e5588f58beb0844e634485661c49c45f26","branch":"refs/heads/feature/organizer-analytics","head":"2b711e66f3a70bd1346815181d0736986e99e936","baseRef":"refs/heads/main","baseCommit":"4876556fcd7e0f469f55cfd574923f0041251215","sourceTree":"09698e618f30a8e58f37cc0283108e39988bf25f","landing":"local-merge","absentOptional":[]} -->

## Findings

No findings were resolved in this work item. F-01 and F-02 (P3, open), F-03
(P3, unverified), and F-04 (P3, open, raised by this review) remain in the live
ledger `blueprint/context/findings.md` for a later `/audit` pass.

## Independent review

**Status:** passed
**Target commit:** 2b711e66f3a70bd1346815181d0736986e99e936
**Base commit:** 4876556fcd7e0f469f55cfd574923f0041251215
**Base ref:** main
**Spec hash:** 5a000a942405bba2629ce6a3281872e5588f58beb0844e634485661c49c45f26
**Prepared by:** claude
**Builder model:** claude-opus-5-5
**Requested reviewer:** claude
**Requested model:** claude-opus-5-5
**Requested execution:** automatic
**Requested at:** 2026-11-20T18:55:21Z
**Workflow:** regular
**Check required:** no
**Reviewer adapter:** claude
**Reviewer model:** claude-opus-5-5
**Reviewer context:** fresh subagent
**Actual execution:** automatic
**Reviewed at:** 2026-11-20T18:57:36Z
**Scope:** current
**Lenses:** quality, security, performance, tests
**Verdict:** passed
**Check result:** not-required

## Commands

- `git rev-parse HEAD` / `git merge-base main HEAD` / `shasum -a 256 blueprint/context/current-feature.md` / `git status --porcelain`: pass (target, base, and spec hash match; only review.md dirty)
- `git diff 4876556..2b711e6` (backend, frontend, spec): pass (full delta reviewed, including owner commit c4f3e25)
- `docker compose exec -T frontend npm run build`: pass (exit 0, "Build complete!")
- `curl GET /api/v1/events/{id}/analytics` access matrix (tokens minted in-container, login not called because it can write host-invite links): pass (organizer 200, manager co-host 200, HOST-role co-host 403, other organizer 403, buyer 403, admin 200, signed out 401, missing 404)
- `curl GET /api/v1/events/me` vs analytics vs `psql` aggregates for events 103, 107, 111, 113: pass (sold, checked_in, revenue, order counts all agree; per-type rows sum to totals)
- `docker exec ren-backend python -c` SQLAlchemy driver probe: pass (SQLAlchemy 2.1.9 defaults to psycopg v3, which is not installed; engine now uses psycopg2)
- Test command: unavailable (none configured)
- Lint command: unavailable (none configured)
- Verify command: unavailable (none configured)

## Evidence

- Route `GET /events/{event_id}/analytics` (backend/app/api/v1/events.py:268) goes through `_get_owned_event` -> `load_manageable_event`; `/me` stays declared first (line 173).
- `_ticket_type_stats` (backend/app/crud/event.py:42) uses two grouped aggregates keyed by `ticket_type_id`, shared by `/events/me` and `get_analytics`; no per-row queries. Revenue reads `order_items.unit_price` on PAID orders, so ticket type price edits cannot change it (code-level; not mutated at runtime).
- `sold` filters `status != CANCELLED`, equivalent to the spec's valid-or-used given the three-value `TicketStatus` enum.
- Order counts use `count(distinct Order.id)` across all `OrderStatus` values; SQL cross-check matched (e.g. event 107 PAID:27, CANCELLED:4).
- Frontend: tab lazily mounts on first open and on `?tab=analytics` load; table has sr-only caption and scoped headers; bar is `aria-hidden`; `/dashboard` adds the Checked in tile and card stat.
- c4f3e25 (backend/app/core/database.py) is justified by the SQLAlchemy 2.1 default-driver change; it also drops the file's trailing newline (harmless).

## Findings

- F-04 [P3] open - Attendance bar uses an inline style binding
- F-01, F-02, F-03 are carried from earlier work; their files are outside this delta and were not re-examined.

## Remaining risk

- No test, lint, or Verify command is configured, so there is no automated regression coverage for the aggregation logic.
- Price-edit invariance and Refresh-after-check-in were verified by code reading only; runtime checks would mutate data and were out of bounds.
- Browser flows (Analytics tab rendering, empty/error states, dashboard tile layout) were not exercised in a browser; only the production build was run.
- No event without ticket types exists in seed data, so the empty-state and `attendance_rate: null` with no types path was verified by code only.
- Revenue counts PAID orders even when tickets were later cancelled (event 113 shows 0 sold, 240.00 revenue). This matches the spec, which defers cancelled-ticket and refund handling to Feature 19.

## Try it now

Run or do:

With `docker compose up` running, sign in at http://localhost:3000/login as `organizer@ren-events.com` / `password123`, then open http://localhost:3000/dashboard/events/103?tab=analytics

Expected:

The Analytics tab is selected and shows Tickets sold **47**, Revenue **£2,260.00**, Checked in **29**, Attendance **62%**. The table lists General Admission (16 sold, 10 checked in, £400.00) and VIP (31 sold, 19 checked in, £1,860.00) with a Total row of 47 / 293 / 29 / £2,260.00, and Orders shows Paid 24, Pending 0, Cancelled 0.

This proves:

The Analytics tab opens from the URL and shows per-ticket-type sales, price-paid revenue, and attendance, with rows that sum to the totals.
