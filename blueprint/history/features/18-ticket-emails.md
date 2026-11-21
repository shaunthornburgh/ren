# Feature: Ticket emails

**From build-plan:** feature 18
**Build attempt:** 1
**Branch:** feature/ticket-emails
**Status:** verified

## Goal

When an order becomes paid, email the buyer an order confirmation that carries
every ticket: the event details, each ticket's QR code as an inline image that
scans straight from the inbox, and the printed code underneath. The email goes
out exactly once per order, on the Stripe webhook's transition to paid, and a
mail failure never breaks the webhook.

## In scope

- Add `segno` (pure-Python QR generator, no dependencies) to
  `backend/requirements.txt`.
- An order confirmation email in `app/core/email.py`: plain-text part plus HTML
  part with one inline PNG QR per ticket (CID images in `multipart/related`).
- Assemble the email's plain data from a paid order in `app/crud/order.py`.
- `crud.order.fulfill` reports whether this call transitioned the order to paid.
  The Stripe webhook schedules the email as a background task only then.

## Out of scope

- Resend button or endpoint, PDF tickets, wallet passes, calendar attachments.
- Emails for refunds, cancellations, or event changes (Feature 19).
- Free-order or non-Stripe fulfilment paths (none exist today).
- A persisted "email sent" flag or delivery retries. Email stays best-effort,
  matching the existing helper.
- Fixing the unescaped HTML in the existing new-event email, or the site-wide
  GBP/`STRIPE_CURRENCY` mismatch.
- Seed data: `scripts/seed_demo_data.py` fulfils orders directly and must not
  send emails.

## Build loop

`workflow.stepReview` is `feature`: build both steps, then stop once for review
of the whole feature. `workflow.checkpointCommits` is `disabled`: no commits per
step; `/complete` makes the feature commit. Work on branch
`feature/ticket-emails`.

## Build steps

- [x] **1. Confirmation email builder.**
  - Add `segno` to `backend/requirements.txt` and rebuild the backend image
    (`docker compose up --build backend`).
  - In `app/core/email.py`, add plain dataclasses (no ORM objects, so they
    survive the request session closing, like `NewEventEmail`):
    - `ConfirmationTicket(type_name: str, code: str)`
    - `ConfirmationEvent(event_id, title, start: datetime, end: datetime,
      location: str | None, is_online: bool, tickets: list[ConfirmationTicket])`
    - `OrderConfirmationEmail(order_id, to: str, buyer_name: str | None,
      total_amount: Decimal, events: list[ConfirmationEvent])`
  - `build_order_confirmation(data) -> EmailMessage`: content per Data /
    contracts below. QR PNGs come from `segno.make_qr(code, error="m")` (standard QR, never Micro QR) written as
    PNG (dark `#111827` on white, default 4-module quiet zone, scale large enough
    for roughly 200 px). Each PNG is attached as a related part with a unique
    `Content-ID` referenced by `<img src="cid:...">`.
  - `send_order_confirmation(data) -> None`: builds and hands the message to the
    existing `_deliver` (console backend in dev, SMTP when enabled), then logs
    one summary line. Never raises.
  - In `app/crud/order.py`, add
    `get_confirmation_email(db, *, order_id) -> OrderConfirmationEmail | None`.
    It returns `None` unless the order exists and is paid. It loads the buyer,
    items, tickets, ticket types, and events with eager loading (no per-ticket
    queries) and groups non-cancelled tickets by event (event `start_datetime`
    order, tickets by id).
  - Check during the step: `zoneinfo.ZoneInfo("Europe/London")` must resolve in
    the backend container. If it doesn't, add `tzdata` to requirements.
  - **Done when:**
    - for a seeded paid order, a `docker exec ren-backend python -c ...` call
      of `get_confirmation_email` plus `build_order_confirmation` produces a
      message with:
      - the subject from the contract
      - a text part listing every ticket code
      - an HTML part
      - exactly one `image/png` part per ticket, each with a matching `cid:`
        reference
    - every PNG decodes (with `jsqr` plus `pngjs`, already in the frontend
      container's `node_modules`) to its ticket's raw code
    - `get_confirmation_email` returns `None` for a pending order and for a
      missing id

- [x] **2. Send once on payment.**
  - Change `crud.order.fulfill` to return `tuple[Order | None, bool]`, where the
    bool is true only when this call moved the order from pending to paid.
    Update both callers: `api/v1/payments.py` and `scripts/seed_demo_data.py`.
    The seed ignores the flag and sends nothing.
  - In `stripe_webhook`, accept `BackgroundTasks`. When `fulfill` reports a
    transition, call `crud.order.get_confirmation_email` and schedule
    `email.send_order_confirmation` with the result. Redeliveries, unpaid
    `completed` events, and expired or failed sessions schedule nothing. The
    webhook still returns `{"received": true}` with 200 in every accepted case.
  - **Done when** (create a fresh pending order via `POST /api/v1/orders` as
    `buyer@ren-events.com`, then post locally signed
    `checkout.session.completed` events to `/api/v1/payments/webhook`, signed
    with the configured `STRIPE_WEBHOOK_SECRET`):
    - the first delivery returns 200, the order is `paid` with tickets issued,
      and `docker logs ren-backend` shows exactly one `[email:console]` entry
      to the buyer whose text lists every new ticket code
    - an identical second delivery returns 200 and logs no second email
    - a `checkout.session.expired` event for another pending order cancels it
      and logs no email
    - `docker exec ren-backend python -m scripts.seed_demo_data` still runs (or
      the changed seed function is exercised) without sending emails
    - if `STRIPE_WEBHOOK_SECRET` is unset in the running container, stop and
      ask rather than changing configuration

- [x] **3. Repair review findings F-05 and F-06.**
  - F-05: collapse whitespace runs (including line breaks) in the event title
    used for the single-event subject, so a title containing a newline still
    produces a valid header and the email is sent.
  - F-06: replace the em dash in the new `noqa` comment in
    `send_order_confirmation` with a hyphen.
  - **Done when:** building a confirmation for synthetic data whose event title
    contains `\n` succeeds, with subject `Your tickets for <title words joined
    by single spaces>`; the paid order 1043 email is unchanged (same subject,
    text, and 2 decodable QR images); and the lines this feature added contain
    no U+2014.

## Files / areas

- `backend/requirements.txt` (`segno`, plus `tzdata` only if needed)
- `backend/app/core/email.py`
- `backend/app/crud/order.py`
- `backend/app/api/v1/payments.py`
- `backend/scripts/seed_demo_data.py` (the `fulfill` call site only)
- No frontend, model, or schema change.

## Data / contracts

**Trigger:** only the Stripe webhook's pending-to-paid transition inside
`crud.order.fulfill`. The order row lock already serialises concurrent
deliveries, so at most one call reports the transition and at most one email is
scheduled per order. Delivery runs in a FastAPI background task after the 200
response. Failures are logged by `_deliver` and never raise.

**Recipient:** the order's buyer, `order.user.email`. Tickets are issued to the
buyer, so the buyer receives all of them.

**Subject:**
- if all tickets are for one event: `Your tickets for <event title>`
- otherwise: `Your tickets for order #<order id>`

**Body (text and HTML carry the same facts):**
- greeting: `Hi <full_name>,`, or `Hi,` when the buyer has no name
- confirmation line with order number `#<id>` and total paid, formatted as
  `<total_amount with 2 decimals> <STRIPE_CURRENCY uppercased>` (for example
  `45.00 USD`). This states the currency actually charged.
- per event, in start order:
  - title
  - when: `start` to `end` converted to `Europe/London`, formatted
    `%a %d %b %Y, %H:%M` plus the zone abbreviation (`GMT`/`BST`). The end
    shows only `%H:%M` when it is on the same day.
  - where: the venue `location`, or `Online: <location URL>` for online events,
    or `Venue TBA` when empty
  - a link to `<FRONTEND_URL>/events/<event_id>`
  - per ticket: ticket type name, the QR image (HTML only, `alt="QR code for
    ticket <formatted code>"`), and the code formatted in groups of four
    joined by `-` (for example `7K3Q-X9MZ-2B4H`, matching the frontend's
    `formatTicketCode`)
- footer: "Show the QR code at the door." plus a link to
  `<FRONTEND_URL>/my-tickets`

**QR payload:** the raw `ticket.code`, unformatted, exactly as
`TicketQrCode.vue` encodes it, so the existing check-in scanner accepts it.

**Escaping:** every interpolated string in the HTML (event title, location,
ticket type name, buyer name) goes through `html.escape`. URLs come from
settings plus integer ids only. The text part is plain text.

**Logging:** the console backend logs the text part (dev only). With SMTP
enabled, only recipient and subject are logged, so ticket codes never reach
production logs.

## Testing

No test runner or Verify command is configured (AGENTS.md Commands).
Verification is manual through `docker exec` scripts, locally signed webhook
posts, and `docker logs`, as listed in each Done when. The fallback gate is the
backend starting cleanly after the image rebuild. No frontend files change, so
the frontend build is not required. Don't claim real SMTP delivery or
inbox rendering; neither is exercised.

## Notes for the AI

- Follow the existing `email.py` style: dataclass payloads, `send_email` and
  `_deliver`, best-effort with no raising, and one aggregate log line.
  Use `EmailMessage.add_alternative(...)` for HTML, then
  `add_related(png_bytes, maintype="image", subtype="png", cid=...)` on the
  HTML part. Generate CIDs with `email.utils.make_msgid`.
- Inline styles are expected inside the email HTML; the frontend no-inline-style
  rule doesn't apply to email markup.
- Keep `fulfill`'s locking and idempotency intact; only the return value
  changes.
- Signing test webhooks: `t=<unix>,v1=<hex HMAC-SHA256 of "<t>.<payload>" with
  the secret>` in the `Stripe-Signature` header. Build it inside the backend
  container so the secret never leaves it or appears in output.
- No new configuration settings.


<!-- blueprint:completion {"schemaVersion":2,"specBytes":10257,"specSha256":"6e736c0a676491fae77f19b49b0ce57dc72e419bf4208892418b70c7119e8c3b","branch":"refs/heads/feature/ticket-emails","head":"4dbee5359cf42ecfb46f3b1390375680acfdd354","baseRef":"refs/heads/main","baseCommit":"7714fc0a195168f1b792c365802f7a8c6356d2ea","sourceTree":"d42406b1538aab4969ad8a62c537055f45632d2f","landing":"local-merge","absentOptional":[]} -->

## Findings

### 18/F-05 [P3] closed - A line break in an event title silently drops the ticket email

**File:** backend/app/core/email.py:243
**Found:** 2026-11-20 by /audit independent (scope: current; lens: quality)
**Why it matters:** The single-event subject interpolates `event.title` into a header. `EventCreate.title` only bounds length, so an organizer can save a title containing `\n` through the API. Python's email policy then raises `ValueError` ("Header values may not contain linefeed or carriage return characters") at `msg["Subject"] = ...` (line 308); `send_order_confirmation` logs and returns, so every buyer of that event gets no tickets email. Reproduced in the backend container with a synthetic `OrderConfirmationEmail`. Header injection itself is blocked by the stdlib, so this is lost mail, not a security break; reaching it needs a newline title, which the frontend input is unlikely to produce.
**Suggested fix:** Collapse whitespace in the subject title, for example `" ".join(data.events[0].title.split())`. No current requirement lost.
**Resolution:** Fixed 2026-11-20 in /implement (spec step 3): `_confirmation_subject` collapses whitespace runs in the title. A synthetic title `Late\nNight\r\n  Jazz` builds with subject `Your tickets for Late Night Jazz`; order 1043's email is unchanged. Closed 2026-11-20 by /audit independent (fresh subagent): re-reviewed backend/app/core/email.py:241-247 at 4dbee53; a synthetic title `Late\nNight\r\n  <Jazz>` built a valid message with subject `Your tickets for Late Night <Jazz>`, and order 1043 still builds with subject `Your tickets for Street Food Friday` and 2 QR parts that decode to its ticket codes. No new defect introduced.

### 18/F-06 [P3] closed - New confirmation code adds an em dash comment

**File:** backend/app/core/email.py:324
**Found:** 2026-11-20 by /audit independent (scope: current; lens: quality)
**Why it matters:** `coding-standards.md` (Writing) bans U+2014 in comments. The new `# noqa: BLE001 — best-effort; log and move on.` copies the existing line 111, so it is drift rather than a defect (same pattern as F-02).
**Suggested fix:** Use `# noqa: BLE001 - best-effort; log and move on.` (or a colon). No current requirement lost.
**Resolution:** Fixed 2026-11-20 in /implement (spec step 3): the new `noqa` comment uses a hyphen; the feature diff adds no U+2014. Closed 2026-11-20 by /audit independent (fresh subagent): email.py:327 now reads `# noqa: BLE001 - best-effort; log and move on.`, and `git diff 7714fc0..4dbee53 -- backend` adds no line containing U+2014.

## Independent review

**Status:** passed
**Target commit:** 4dbee5359cf42ecfb46f3b1390375680acfdd354
**Base commit:** 7714fc0a195168f1b792c365802f7a8c6356d2ea
**Base ref:** main
**Spec hash:** 6e736c0a676491fae77f19b49b0ce57dc72e419bf4208892418b70c7119e8c3b
**Prepared by:** claude
**Builder model:** claude-opus-5-5
**Requested reviewer:** claude
**Requested model:** claude-opus-5-5
**Requested execution:** automatic
**Requested at:** 2026-11-20T20:50:52Z
**Workflow:** regular
**Check required:** no
**Reviewer adapter:** claude
**Reviewer model:** claude-opus-5-5
**Reviewer context:** fresh subagent
**Actual execution:** automatic
**Reviewed at:** 2026-11-20T20:52:49Z
**Scope:** current
**Lenses:** quality, security, performance, tests
**Verdict:** passed
**Check result:** not-required

## Handoff

Review the active spec and the complete `<base>..<target>` delta in a fresh
session or isolated subagent without the builder conversation. Run all Audit lenses from scratch.
Run Check when required above. Do not edit product code, accept findings, or
reuse the existing findings as the review scope.

## Commands

- `git rev-parse HEAD` / `git merge-base main HEAD` / `shasum -a 256 blueprint/context/current-feature.md` / `git status --porcelain --untracked-files=all`: pass (HEAD, merge base, and spec hash match the request; only review.md and findings.md modified)
- `git diff 7714fc0..4dbee53 -- backend`: pass (full delta reviewed: payments.py, email.py, crud/order.py, requirements.txt, seed_demo_data.py; no added U+2014)
- `docker exec -i ren-backend python -` (build-only script: `get_confirmation_email` + `build_order_confirmation` for paid order 1043, pending order 1131, a missing id, and synthetic multi-event data with HTML-special and newline input): pass
- `docker exec -i ren-frontend node` (jsqr + pngjs decode of all 5 generated PNGs): pass (each decodes to its raw ticket code, standard QR version 1, 174x174 px)
- `docker exec -i ren-backend python -` (SQL statement count for `get_confirmation_email`, cold and warm session): pass (5 statements both ways, independent of ticket count)
- `docker exec ren-db psql SELECT` (order status counts, order 1043 tickets): pass
- `curl GET http://localhost:8000/api/v1/events`: pass (200; backend running with segno 1.6.6 and Europe/London zone resolving)
- Test runner, linter, Verify command: unavailable (none configured)
- `/check`: not run (not required by the request)

## Evidence

- Order 1043: subject `Your tickets for Street Food Friday`; structure multipart/alternative > text/plain + multipart/related(text/html + 2 image/png); text lists both VALID codes; cancelled ticket 1426 correctly omitted; every image Content-ID has a matching `cid:` reference.
- `get_confirmation_email` returns None for pending order 1131 and for a missing id.
- Synthetic data: buyer name, title, location, and ticket type with `<`, `&`, `"` are escaped in HTML; URLs are settings plus integer ids; ticket codes come from a fixed alphanumeric alphabet; a title with `\n`/`\r\n` yields subject `Your tickets for Late Night <Jazz>`; times convert to BST/GMT; multi-event subject is `Your tickets for order #7`.
- `fulfill` keeps `with_for_update` locking and returns `(order, True)` only after the pending-to-paid commit; the webhook schedules the background task only on that flag, so redeliveries and expired/failed sessions schedule nothing. Signature verification is unchanged and precedes all processing.
- With SMTP enabled, `_deliver` logs only recipient and subject; `send_order_confirmation` logs only the order id and outcome.
- Seed caller unpacks the tuple and sends nothing.

## Findings

- F-05 [P3] closed (repair verified)
- F-06 [P3] closed (repair verified)
- F-07 [P3] open (new, non-blocking: `build_order_confirmation` exceeds the 50-line function guideline)
- No P0 or P1 findings open or fixed.

## Remaining risk

- No test runner, linter, or Verify command is configured; no automated regression coverage for the email builder or the webhook's send-once flag.
- The live webhook path (signed delivery, redelivery, expiry) was not re-executed in this review because it would mutate data; send-once behaviour is verified by code reading plus query-count simulation only.
- If `get_confirmation_email` fails after `fulfill` commits (database error only), the webhook returns 500, Stripe's retry sees the order already paid, and that order's email is never sent. Accepted by the spec's best-effort, no-retry contract.
- Real SMTP delivery and inbox rendering of CID images were not exercised.

## Try it now

Run or do:

```bash
docker exec ren-backend python -c "from app.core.database import SessionLocal; from app import crud; from app.core.email import build_order_confirmation as b; m=b(crud.order.get_confirmation_email(SessionLocal(), order_id=1043)); print(m['Subject']); print(m.get_body(('plain',)).get_content()); print(sum(p.get_content_type()=='image/png' for p in m.walk()), 'QR images')"
```

Expected:

```
Your tickets for Street Food Friday
Hi Casey Buyer,

Your order #1043 is confirmed. Total paid: 15.00 GBP.

Street Food Friday
When: Mon 23 Nov 2026, 17:00-23:00 GMT
Where: Kirkgate Market, George St, Leeds LS2 7HY
http://localhost:3000/events/112
- Entry: 1H2J-0QPA-C5ST
- Entry: 5GZ6-YKEG-GWVP

Show the QR code at the door.
Your tickets: http://localhost:3000/my-tickets

2 QR images
```

This proves:

A paid order produces the confirmation email with the event subject, UK-time event details, every ticket's printed code, and one inline QR image per ticket, built without sending or changing data.
