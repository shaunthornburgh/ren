# Feature: Admin area

**From build-plan:** feature 16
**Build attempt:** 1
**Branch:** feature/admin-area
**Status:** verified

## Goal

Give the existing `admin` role a UI to manage the platform. Admins can find
users, change a user's role, and activate or deactivate accounts. They can also
see every event in any status, change an event's status, and jump to the
existing management page for any event. Today the role bypasses ownership checks
in the API but has no screens, and there is no way to promote an organizer
except through the seed script.

## In scope

- Admin-only API under `/api/v1/admin`: list/search users, update a user's
  `role` / `is_active`, list/search all events.
- Self-lockout guard: an admin cannot change their own role or deactivate
  themselves.
- Deactivation takes effect on existing sessions: `GET /auth/me` rejects
  inactive users, so the frontend clears the token.
- Bootstrap: a `scripts.set_user_role` one-off script to make the first admin,
  plus an `admin@ren-events.com` demo login in the seed.
- Frontend: `admin` route middleware, an **Admin** header link for admins,
  `/admin` (users) and `/admin/events` pages.

## Out of scope

- Deleting users or events, editing other users' profiles or passwords,
  impersonation.
- Ticket-holder handling when an event is cancelled (refunds, notices): this is
  Feature 19. Admin status changes reuse the existing `PUT /events/{id}`
  behaviour unchanged.
- Analytics or revenue views (Feature 17), audit logs, bulk actions.
- Changing the existing organizer dashboard beyond what Step 4's check requires.

## Build loop

`workflow.stepReview` is `feature`: build all steps, then stop once for review
of the whole feature. `workflow.checkpointCommits` is `disabled`: no commits per
step; `/complete` makes the feature commit. Work on branch `feature/admin-area`.

## Build steps

- [x] **1. Admin users API, session enforcement, bootstrap.**
  - Add `app/api/v1/admin.py` (`APIRouter(prefix="/admin", tags=["admin"])`),
    included in `app/main.py`. Every handler depends on
    `require_role(UserRole.ADMIN)`.
  - `GET /admin/users` and `PATCH /admin/users/{user_id}` per Data / contracts,
    with CRUD in `app/crud/user.py` (`get_multi_for_admin`, `admin_update`) and
    `AdminUserUpdate` in `app/schemas/user.py`.
  - `GET /auth/me` switches to `get_current_active_user`.
  - `backend/scripts/set_user_role.py`: `python -m scripts.set_user_role <email> <role>`.
    It exits non-zero with a message if the email isn't found or the role is invalid,
    is idempotent, and prints the result.
  - Seed: add `("admin", "admin@ren-events.com", "Ada Admin", UserRole.ADMIN)`
    to `LOGINS` and the docstring login list.
  - **Done when:** at `/docs`, an admin token lists, searches and filters users
    and can PATCH another user's role and `is_active`. A customer or organizer
    token gets 403 and no token gets 401. A self-PATCH that changes role or
    deactivates gets 400. Once a user is deactivated, their existing token gets
    403 on `/auth/me` and they can't log in. The script promotes a user by email
    and rejects an unknown one.

- [x] **2. Admin events API.**
  - `GET /admin/events` per Data / contracts, with CRUD `crud.event.get_multi_for_admin`
    and schema `AdminEventRead` in `app/schemas/event.py`.
  - **Done when:** an admin sees draft, published and cancelled events from
    every organizer, newest start first, with `organizer_name`. `q` and `status`
    filter correctly. Non-admins get 403.

- [x] **3. Admin guard, nav, and Users page.**
  - `app/middleware/admin.ts` (modelled on `organizer.ts`, `role === 'admin'`,
    otherwise redirect to `/`; unauthenticated users go to `/login?redirect=`).
  - `AppHeader.vue` (and mobile menu) shows **Admin** -> `/admin` only for admins;
    check `AccountMenu.vue` for a matching nav list and add it there too if one exists.
  - `pages/admin/index.vue` (Users): Users | Events tab links, search input
    (debounced or submit), role filter, table/cards with name, email, role,
    status, joined date. Each row has a labelled role `<select>` and an
    Activate/Deactivate button. Deactivating asks for confirmation first.
  - Types in `types/api.ts`: `AdminUserUpdate`, `AdminEventRead`.
  - **Done when:** in the browser, an admin can search, filter, change a role
    and toggle active, and each change persists after reload. The admin's own
    row has its controls disabled with an explanation. A non-admin visiting
    `/admin` is sent home. Loading, empty ("No users match"), and error states
    render. `npm run build` passes.

- [x] **4. Events page.**
  - `pages/admin/events.vue`: same tabs, search by title, status filter, list
    with title, organizer, calendar id/date, status badge. Each event has a
    status `<select>` (draft / published / cancelled) saved via the existing
    `PUT /events/{id}` with `{ status }`, plus links to `/events/{id}` and
    `/dashboard/events/{id}`. Changing to `cancelled` asks for confirmation.
  - **Check:** `dashboard/events/[id]/index.vue` loads `/calendars/me` for its
    calendar dropdown, so for an event an admin doesn't own the event's calendar
    may be missing. Confirm saving from that page as an admin doesn't change or
    blank `calendar_id`. If it does, either fix it minimally (send `calendar_id`
    only when changed) or drop the Manage link and report back. Don't redesign
    the page.
  - **Done when:** an admin can filter all events and change one's status. The
    change shows on the public listing (published shows, draft hides), and a
    draft-to-published change still notifies followers through the existing
    path. Links open the right pages. Empty, loading, and error states render.
    `npm run build` passes.

## Files / areas

- Backend: `app/api/v1/admin.py` (new), `app/main.py`, `app/api/v1/auth.py`,
  `app/crud/user.py`, `app/crud/event.py`, `app/schemas/user.py`,
  `app/schemas/event.py`, `scripts/set_user_role.py` (new),
  `scripts/seed_demo_data.py`.
- Frontend: `app/middleware/admin.ts` (new), `app/pages/admin/index.vue` (new),
  `app/pages/admin/events.vue` (new), `app/components/AppHeader.vue`,
  possibly `AccountMenu.vue`, `app/types/api.ts`; possibly
  `app/pages/dashboard/events/[id]/index.vue` (Step 4 check only).
- No schema change: `users.role` and `users.is_active` already exist.

## Data / contracts

All under `/api/v1`, `require_role(UserRole.ADMIN)` (401 without a token, 403
for an inactive or non-admin user). Errors use `{ "detail": "<sentence>" }`.

**`GET /admin/users`** -> `200 list[UserRead]`
- Query: `q` (str, optional, trimmed, max 100), case-insensitive substring match
  on `email`, `full_name`, `display_name`. `role` (`UserRole`, optional).
  `skip` (int >= 0, default 0). `limit` (1-100, default 50).
- Order: `created_at` desc, then `id` desc. The frontend shows **Load more**
  while a page returns `limit` rows.

**`PATCH /admin/users/{user_id}`** body `AdminUserUpdate` -> `200 UserRead`
- `AdminUserUpdate`: `role: UserRole | None`, `is_active: bool | None`; apply
  with `exclude_unset=True`; an empty body is a 200 no-op.
- 404 `"User not found."` if missing.
- 400 `"You can't change your own role or deactivate your own account."` when
  `user_id == current_user.id` and the body sets a different `role` or sets
  `is_active=false`. The actor always comes from `current_user`, never the body.
- Because the acting admin can't demote themselves, at least one active admin
  always remains.

**`GET /admin/events`** -> `200 list[AdminEventRead]`
- `AdminEventRead` = `EventRead` + `organizer_name: str` (via
  `crud.user.display_name_for`; no organizer email).
- Query: `q` (title, case-insensitive substring, trimmed, max 100), `status`
  (`EventStatus`, optional), `skip`, `limit` (as above).
- Order: `start_datetime` desc, `id` desc. Eager-load the organizer to avoid
  N+1 queries.

**Event status change:** existing `PUT /events/{event_id}` with
`{ "status": "<draft|published|cancelled>" }`. Admins already pass
`load_manageable_event`. Unchanged side effects: publishing notifies followers.

**`GET /auth/me`:** now 403 `"Inactive user"` for deactivated accounts; the
frontend's existing `fetchUser` catch clears the token.

**Frontend types (`types/api.ts`):**
`AdminUserUpdate { role?: UserRole; is_active?: boolean }`,
`AdminEventRead extends EventRead { organizer_name: string }`.

## Testing

No test runner or Verify command is configured (AGENTS.md Commands).
Verification is manual:
- API: `/docs` or curl with seeded tokens (`admin@`, `organizer@`, `buyer@`,
  password `password123`) after re-running `seed_demo_data`. Cover 200 / 400 /
  401 / 403 / 404.
- Frontend: `docker compose exec frontend npm run build`, plus browser checks
  of the flows in each Done when (screenshots where available).
- Don't claim test coverage that wasn't run.

## Implementation notes

- **Step 4 check result:** saving from `dashboard/events/[id]` kept
  `calendar_id`, but a viewer whose own calendars didn't include the event's
  calendar couldn't save at all. The required `<select>` had no matching option,
  and the submit button was disabled when they had no calendars. Co-host
  managers already hit this. Minimal fixes:
  - `OrganizerEventForm.vue` keeps the event's current calendar as a
    "Current calendar" option.
  - `PUT /events/{id}` checks calendar ownership only when `calendar_id`
    actually changes. Moving an event to another calendar still requires
    owning the target.
- **Verification (2026-11-19, Docker stack, seeded):**
  - API: admin list, search, role filter, paging, `limit=101` -> 422. Non-admin
    -> 403, anonymous -> 401. Self-demote and self-deactivate -> 400, a
    same-role self-PATCH -> 200, unknown user -> 404. Promoting buyer let them
    call `/events/me`. Deactivating them made their old token 403 on `/auth/me`
    and blocked login; restoring brought both back.
  - Admin events: all 3 statuses from multiple organizers, newest first, with
    `organizer_name`. `q` and `status` filters work; a bad status -> 422.
  - Admin draft -> published made event 106 appear publicly and created 6
    follower notifications; back to draft hid it. A co-host manager resending
    the same `calendar_id` -> 200; moving to an unowned calendar -> 403 and the
    calendar is unchanged.
  - `set_user_role`: promote, idempotent rerun, unknown email exits 1, invalid
    role is rejected by argparse.
  - `docker compose exec frontend npm run build`: Build complete.
  - Browser (Chrome): Admin nav and Users list; Load more 50 -> 58, then
    hidden; search; role change persisted in the DB and was announced; self row
    disabled with note. Events: status filter, links, status change both ways
    with announcement, empty state "No events match". Manage page for event
    106 shows "Current calendar", saves with `calendar_id` 46 intact. An
    organizer visiting `/admin` is redirected home with no Admin link.
  - Not exercised in the browser: the Deactivate and Cancel confirm dialogs
    (they block automation) and load-error states. Their API paths were
    verified.

## Notes for the AI

- Follow the four-layer pattern and route conventions in `coding-standards.md`.
  Use one-line handler docstrings ("Admin only.").
- Render user-supplied text (names, emails, titles) with Vue interpolation
  only; no `v-html`.
- Accessibility: every per-row control needs an accessible name (for example
  `aria-label="Role for {email}"`). Show per-row save errors inline next to the
  row and restore the previous value on failure. Announce successful saves
  through a polite `aria-live` region. Disabled self-row controls carry a
  visible "This is you" note.
- Use `useAsyncData(..., { server: false })`, `useApi().apiFetch`, Tailwind
  with `dark:` variants, Boxicons, and `purple-600` accents. Match the existing
  dashboard card style.
- Role changes take effect on the target's next request (role is read from the
  DB per request). Their header nav updates on their next `fetchUser`, which is
  acceptable.
- Escaping `%` / `_` in `q` is unnecessary; a plain `ilike(f"%{q}%")` is fine.

## Open questions

Non-blocking. The spec uses the defaults below; say if you want otherwise.

- **Event management scope:** list, status change, and links to existing pages.
  No admin event deletion. Hard deletes cascade to orders and tickets.
- **Admin bootstrap:** a CLI script plus a seeded demo admin. No env-var
  auto-promotion.


<!-- blueprint:completion {"schemaVersion":2,"specBytes":12490,"specSha256":"be0d267c7b61b2bba984ab3b903744f7fe64d212e551fd7ce574e04261f7dc05","branch":"refs/heads/feature/admin-area","head":"daaafcf2d73bbea4e0df853e6b5071b56a4c2fcd","baseRef":"refs/heads/main","baseCommit":"1a3f19dd5225cc60e698b1438ec227ca3960dc4d","sourceTree":"a6e178cd1f77cce989b3908213312b52e0bded1f","landing":"local-merge","absentOptional":[]} -->

## Findings

No findings were resolved in this work item. F-01 and F-02 (P3, open) and F-03
(P3, unverified) remain in the live ledger `blueprint/context/findings.md` for a
later `/audit` pass.

## Independent review

**Status:** passed
**Target commit:** daaafcf2d73bbea4e0df853e6b5071b56a4c2fcd
**Base commit:** 1a3f19dd5225cc60e698b1438ec227ca3960dc4d
**Base ref:** main
**Spec hash:** be0d267c7b61b2bba984ab3b903744f7fe64d212e551fd7ce574e04261f7dc05
**Prepared by:** claude
**Builder model:** claude-opus-5-5
**Requested reviewer:** claude
**Requested model:** claude-opus-5-5
**Requested execution:** automatic
**Requested at:** 2026-11-20T02:25:30Z
**Workflow:** regular
**Check required:** no
**Reviewer adapter:** claude
**Reviewer model:** claude-opus-5-5
**Reviewer context:** fresh session
**Actual execution:** manual
**Reviewed at:** 2026-11-20T02:36:23Z
**Scope:** current
**Lenses:** quality, security, performance, tests
**Verdict:** passed
**Check result:** not-required

## Handoff

Review the active spec and the complete `1a3f19dd5225cc60e698b1438ec227ca3960dc4d..daaafcf2d73bbea4e0df853e6b5071b56a4c2fcd` delta in a fresh
session or isolated subagent without the builder conversation. Run all Audit lenses from scratch.
Run Check when required above. Do not edit product code, accept findings, or
reuse the existing findings as the review scope.

## Commands

- `git rev-parse HEAD` / `git merge-base main HEAD` / `shasum -a 256 blueprint/context/current-feature.md`: pass (match request)
- `docker compose exec -T frontend npm run build`: pass (Build complete)
- `curl` read-only API smoke checks against http://localhost:8000: unavailable (API did not respond, health check timed out)
- Lint: unavailable (none configured)
- Test: unavailable (none configured)

## Evidence

- Reviewed all 18 files in the delta: backend admin router, auth `/me`, events `PUT` calendar check, user/event CRUD and schemas, seed and `set_user_role` scripts; frontend admin middleware, AdminTabs, AppHeader, OrganizerEventForm, admin users/events pages, API types.
- All admin handlers depend on `require_role(UserRole.ADMIN)`, which builds on `get_current_active_user`; no API route uses bare `get_current_user`, and `get_current_user_optional` already drops inactive users, so deactivation applies to existing tokens.
- Self-lockout guard uses `current_user`, never the body; `exclude_none` makes explicit nulls a no-op.
- `GET /admin/events` eager-loads organizer; `EventRead` has no relationship fields, so no N+1. Paging bounded at 100.
- User-supplied text rendered by interpolation only; no `v-html` in the delta.
- Calendar-ownership check now runs only on an actual `calendar_id` change; moving to an unowned calendar still requires ownership.

## Findings

- F-01 [P3] open, F-02 [P3] open, F-03 [P3] unverified

## Remaining risk

- API runtime behavior not re-exercised in this session (backend unreachable); relied on code reading plus the builder's recorded verification.
- No test runner, linter, or CI configured; no automated coverage of the admin guards or self-lockout logic.
- Browser flows, including Deactivate/Cancel confirm dialogs and load-error states, not exercised by this review.

## Try it now

Run or do:

With `docker compose up` running and demo data seeded, sign in at
http://localhost:3000/login as `admin@ren-events.com` (seed password
`password123`), click **Admin** in the header, type `casey` in **Search users**
and press Enter.

Expected:

One row, **Casey Buyer**, with a CUSTOMER badge, a role dropdown labelled
"Role for buyer@ren-events.com", and a **Deactivate** button. Your own row (search
`admin`) shows "This is you" with its controls disabled.

This proves:

The admin-only Users page is reachable for admins and searches users, and the
self-lockout guard is shown in the UI.
