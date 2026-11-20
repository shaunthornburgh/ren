# Findings

> **Generated file.** The findings ledger: review findings raised by `/audit`
> against the work in progress, each with a durable ID, severity (P0-P3), and
> status. `/implement` marks repaired findings `fixed`, a later `/audit` pass
> moves them to `closed`, and `/complete` refuses to land while any P0 or P1
> finding is `open` or `fixed`, then archives resolved findings with the work
> and resets this file.

### F-01 [P3] open - Load more can append rows from a superseded filter

**File:** frontend/app/pages/admin/index.vue:44 (same pattern in frontend/app/pages/admin/events.vue:44)
**Found:** 2026-11-20 by /audit independent (scope: current; lens: quality)
**Why it matters:** `loadMore` captures the current `appliedQ` / filter when it starts. If the admin changes the role/status filter or submits a new search while that request is in flight, `useAsyncData` refetches page 0 for the new filter, and the older Load more response then resolves and is appended to the new list. The list briefly mixes rows that don't match the visible filter and `hasMore` reflects the old query. Needs a slow request to hit; no data is changed.
**Suggested fix:** Remember the filter key (or a request counter) at the start of `loadMore` and drop the response if it changed, or hide/disable Load more while `pending`. No current requirement lost.
**Resolution:**

### F-02 [P3] open - New code adds em dashes against the writing standard

**File:** frontend/app/pages/admin/index.vue:191
**Found:** 2026-11-20 by /audit independent (scope: current; lens: quality)
**Why it matters:** `coding-standards.md` (Writing) bans U+2014 in generated content including comments. The new self-row note ("This is you — you can't ...") is user-facing copy, and the new comments at frontend/app/middleware/admin.ts:15 and backend/scripts/set_user_role.py:14 also use em dashes (both copied from existing files, so this is drift, not a defect).
**Suggested fix:** Rephrase with a comma or period, for example "This is you. You can't change your own role or status." and "Signed in but not permitted, so send home rather than to login." No current requirement lost.
**Resolution:**

### F-03 [P3] unverified - Two admins deactivating each other concurrently can leave no active admin

**File:** backend/app/api/v1/admin.py:56
**Found:** 2026-11-20 by /audit independent (scope: current; lens: security)
**Why it matters:** The spec states at least one active admin always remains because an admin can't demote or deactivate themselves. That holds sequentially, but two simultaneous PATCHes (A deactivates B, B deactivates A) both pass `require_role` before either commits. Recovery is possible: `scripts.set_user_role` can promote another active user to admin, though it cannot reactivate an account. Not reproduced; requires near-simultaneous requests by two admins.
**Suggested fix:** Accept as a known edge for this platform size, or document that recovery path in the script docstring. Locking is not warranted without a real requirement.
**Resolution:**

### F-04 [P3] open - Attendance bar uses an inline style binding

**File:** frontend/app/components/EventAnalytics.vue:72
**Found:** 2026-11-20 by /audit independent (scope: current; lens: quality)
**Why it matters:** `coding-standards.md` (Styling) says "No inline styles", and this `:style="{ width: ... }"` on the decorative attendance bar is the only `style`/`:style` binding in `frontend/app`. It is standards drift, not a defect: the bar is `aria-hidden` and the text percentage carries the value.
**Suggested fix:** Replace the two nested divs with a native `<progress :value="data.attendance_rate ?? 0" max="1" aria-hidden="true">` styled with Tailwind classes (or drop the bar, which the spec makes optional with "Any attendance bar"). No current requirement lost.
**Resolution:**
