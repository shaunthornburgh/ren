# Coding Standards

> Rewritten by `/adopt` to match the conventions the Ren codebase actually uses.
> Follow existing code first; these rules describe it.

## Project Layout

- `backend/` - FastAPI app (`backend/app/`), one-off scripts (`backend/scripts/`), local uploads
- `frontend/` - Nuxt 4 app with source under `frontend/app/`
- `docker-compose.yml` - db, backend, frontend; always respect this setup

## Backend (Python / FastAPI)

### Layers

Each resource is split across the same four layers. Add a new resource the same way.

- `app/models/<resource>.py` - SQLAlchemy model; register it in `app/models/__init__.py`
- `app/schemas/<resource>.py` - Pydantic v2 schemas
- `app/crud/<resource>.py` - module-level DB functions; export the module from `app/crud/__init__.py`
- `app/api/v1/<resource>.py` - `APIRouter` with `prefix` and `tags`; include it in `app/main.py` under `settings.API_V1_PREFIX`
- `app/deps.py` - shared dependencies: `get_db`, `get_current_user`, `get_current_active_user`, `get_current_user_optional`, `require_role`, `load_manageable_event`
- `app/core/` - config, database, security, and integrations (`stripe.py`, `email.py`, `uploads.py`)

### Models

- SQLAlchemy 2.0 declarative style: `Mapped[...]` with `mapped_column(...)`
- Relationships use `back_populates`; import related models under `TYPE_CHECKING`
- Foreign keys declare `ondelete` and `index=True`
- Timestamps: `created_at` / `updated_at` as `DateTime(timezone=True)` with `server_default=func.now()`
- Enums subclass `(str, enum.Enum)` and map with a named `Enum(...)` column type
- Money uses `Numeric(10, 2)` in the DB and `Decimal` in schemas

### Schemas

- Pattern per resource: `<Name>Base`, `<Name>Create`, `<Name>Update` (all fields optional), `<Name>Read`
- `Read` schemas set `model_config = ConfigDict(from_attributes=True)`
- Validate with `Field(...)` constraints (`min_length`, `max_length`, `ge`, ...)

### CRUD

- Plain functions taking `db: Session` and keyword-only args (`*, id`, `*, obj_in`, `*, db_obj`)
- Queries use `select(...)` with `db.scalars(...)`; single lookups use `db.get(...)`
- Updates apply `obj_in.model_dump(exclude_unset=True)`
- CRUD functions commit and refresh

### Routes

- Sync `def` handlers with `Annotated[..., Depends(...)]` dependencies
- Declare `response_model` and `status_code` (for example `HTTP_201_CREATED` on create)
- Errors via `HTTPException` with `status.HTTP_*` and a short sentence `detail`
- Small private helpers like `_get_event_or_404` for repeated lookups
- One-line docstring per handler stating who may call it (public, owner, admin)

### Authorization

- Never trust a client-supplied user id; use the resolved `current_user`
- Event management goes through `load_manageable_event` (owner, accepted co-host, or admin)
- Role-gated endpoints use `require_role(UserRole.ORGANIZER, UserRole.ADMIN)`
- Check that nested resources belong to the parent in the path (for example `ticket_type.event_id == event_id`)

### Schema changes

- No Alembic. New tables are created by `Base.metadata.create_all` on startup.
- Changes to existing tables ship as an idempotent script in `backend/scripts/`
  (`ALTER TABLE ... IF NOT EXISTS`, backfill, then constraints), run with
  `docker exec ren-backend python -m scripts.<name>`.

### Integrations

- Settings come from `app.core.config.settings` (pydantic-settings, env vars); never hardcode secrets
- Email is best-effort: helpers in `core/email.py` never raise; send from background tasks using plain dataclasses, not ORM objects
- Stripe webhooks must verify the signature and be idempotent
- Log under the `app` logger via `logging.getLogger(__name__)`

## Frontend (Nuxt 4 / Vue 3 / TypeScript)

### File Organization

- Pages: `app/pages/` (file-based routing, `[id].vue` for dynamic routes); organizer tools under `pages/dashboard/`
- Components: flat in `app/components/`, PascalCase (`TicketTypeManager.vue`), auto-imported
- Composables: `app/composables/useX.ts` (`useApi`, `useAuth`, `useFormat`, `useGoogleMaps`)
- Route guards: `app/middleware/` (`auth`, `organizer`)
- API types: all request/response types in `app/types/api.ts`, mirroring backend schemas (`XRead`, `XCreate`, `XUpdate = Partial<XCreate>`)

### Vue

- `<script setup lang="ts">` single-file components
- Typed props with `defineProps<{ ... }>()`
- Call the backend through `useApi().apiFetch<T>()`, never raw `fetch`
- Load data with `useAsyncData(key, ..., { server: false, default })` since auth lives in localStorage
- Local form state with `reactive`/`ref`; show errors inline via a `formError` ref
- Shared state via `useState`

### Styling

- Tailwind utility classes (Tailwind v3 via `@nuxtjs/tailwindcss`, `tailwind.config.js`)
- Purple accent (`purple-600`), gray neutrals, Boxicons (`bx` classes) for icons
- Support dark mode with `dark:` variants (class strategy)
- No inline styles

## Naming

- Python: snake_case modules, functions, and variables; PascalCase classes; SCREAMING_SNAKE_CASE constants
- TypeScript: camelCase functions; PascalCase types and components
- API paths: kebab-case plural nouns (`/events/{event_id}/ticket-types`)

## Testing

Testing is opt-in and **not yet set up** in Ren: there is no test runner, no
tests, no linter, and no CI. Until a `test` command is declared in the Commands
section of `AGENTS.md`, verify work with the running app (Docker Compose), API
calls against `http://localhost:8000/docs`, browser screenshots, and
`npm run build` for the frontend.

**The opt-in switch is one signal: a `test` command in the Commands section of
`AGENTS.md`.** Once declared, tests become a gate for logic-bearing steps.
Adding the runner is a deliberate step (`/tests`), never a silent mid-step install.

- **What to test:** pure logic where a wrong answer is possible: CRUD logic like
  inventory reservation and order fulfilment, permission checks, code generation,
  validators, formatters.
- **What not to test:** Vue components and integration surfaces driving a real
  browser or Stripe. Verify those with screenshots and the build.
- **The gate (when a runner is configured):** a step that adds in-scope logic ships
  a passing test in the same diff; the test command must be green before approval,
  checkpoint commits, and `/complete`.
- An empty suite should fail, not pass.
- Stack binding: pytest for the backend; Vitest for any frontend logic.

When `AGENTS.md` declares a `Verify` command, treat it as the umbrella automated
gate. `/ci` owns Verify and CI setup.

## Browser Verification

- Browser automation is separately opt-in through `/tests browser`.
- Without a `Browser tests` command, use the dev server, screenshots, and API output.
- Browser evidence matters most for checkout, check-in scanning, forms, and
  dashboard flows.

## Code Quality

- No commented-out code unless specified
- No unused imports or variables
- Keep functions under 50 lines when possible

## Comments

Write code that explains itself; comment only what the code cannot say.

- Comment the **why**, not the **what**. Delete any comment that restates the code.
- No banner blocks, section dividers, or narration of obvious code.
- A comment earns its place when it captures a non-obvious decision, a gotcha, or
  why a value is what it is (the existing bcrypt pin comment is a good example).
- One-line docstrings on modules, classes, and public functions are the house style;
  don't repeat the signature.

## Writing

- No em dashes (U+2014) in generated content: docs, comments, commit messages,
  specs. They read as AI-generated.
- Use a hyphen for `term - description` separators; rephrase prose with commas,
  parentheses, or a colon. Avoid en dashes and the ellipsis character too.
