# CampusKobo Backend Skill Context

## Product Reality

CampusKobo is a real student-finance product, not a demo backend.
Every new feature should be implemented with production expectations:

- low latency on auth and dashboard paths
- predictable response times under load
- secure handling of identity, money, and support data
- migration-safe schema changes
- no feature work that silently breaks onboarding, auth, or budgeting flows

The backend should be treated as a product system with real operational expectations:

- auth flows must be trustworthy
- onboarding must be consistent across sign-up methods
- money-related data must remain auditable and predictable
- database changes must be reversible and environment-safe
- development and production database targets must stay clearly separated

## Product Context From The Figma

The mobile product flows visible in the Figma are:

- splash and onboarding
- email and Google sign up / login
- goal-based onboarding
- budget setup
- category setup
- first expense creation
- dashboard summary
- expenses tracking
- budgets
- savings goals
- learning hub content
- notifications
- security and privacy
- FAQ and contact support

The onboarding journey is core to activation:

1. user signs up or logs in
2. user chooses a goal
3. user sets an initial budget
4. user selects starter categories
5. user logs first expense
6. user reaches the first success state

Any auth feature must preserve this onboarding state model.

Product-level interpretation:

- onboarding is not cosmetic; it is the activation funnel
- budget setup is a first-class feature, not a later enhancement
- expense tracking is the core daily habit loop
- savings and learning are retention features layered on top of the core money workflow
- security, notification, and support settings are necessary product surfaces, not admin afterthoughts

## Current Backend Shape

The backend is built with:

- FastAPI
- async SQLAlchemy sessions
- Alembic migrations
- JWT access and refresh tokens
- email verification codes
- Google identity token verification
- Brevo SMTP email delivery
- environment-driven database selection
- Dockerized runtime with isolated Compose database support

Current project shape:

- `app/api/routes`
  - FastAPI route layer
- `app/services`
  - business logic layer
- `app/models`
  - SQLAlchemy ORM models
- `app/schemas`
  - request/response DTOs
- `app/integrations`
  - external providers such as Google identity and email
- `app/db`
  - engine, session, and local bootstrap
- `alembic`
  - schema migrations
- `Dockerfile`
  - container image for the API
- `docker-compose.yml`
  - isolated API + PostgreSQL runtime used only when Compose is explicitly started

Architectural rule:

- route handlers should stay thin
- services should hold business logic
- integrations should isolate external provider details
- settings should be the single place where environment-specific connection behavior is resolved

Core backend domains:

- `auth`
- `users`
- `onboarding`
- `dashboard`
- `expenses`
- `budgets`
- `savings`
- `learning`
- `notifications`
- `support`

## Environment And Database Rules

Current environment model:

- `APP_ENV=development`
  - uses `DEVELOPMENT_DATABASE_URL`
  - intended for SQLite async by default
- `APP_ENV=production`
  - uses `PRODUCTION_DATABASE_URL`
  - intended for PostgreSQL via `asyncpg`
- `DATABASE_URL`
  - explicit override for either environment

Docker runtime rule:

- Docker Compose provides its own `DATABASE_URL` pointing to its own Postgres container
- Docker must not override or mutate the normal local environment workflow unless Compose is being used
- local development and production env switching logic must continue to work outside Docker exactly as before

Important implementation details:

- the app and Alembic must use the same resolved database URL
- PostgreSQL URLs are normalized to `postgresql+asyncpg://`
- query params like `sslmode=require` are normalized for `asyncpg`
- Supabase pooler connections may need `statement_cache_size=0`

Agent guidance:

- if you are debugging local feature work, prefer development SQLite unless the issue is Postgres-specific
- if you are debugging enums, migrations, pooling, or SSL, reproduce against PostgreSQL
- do not mix local SQLite assumptions into production migration logic
- if a migration partially failed in Postgres, inspect leftover tables, indexes, and enum types before rerunning
- if debugging a Docker-only issue, inspect Compose-provided env vars before touching the core settings model

## Current Auth Surface

Routes currently expected in the backend:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/resend-verification`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/auth/change-email`
- `POST /api/v1/auth/create-pin`
- `POST /api/v1/auth/logout`

User-level account outcomes currently supported:

- standard email account creation
- Google account creation and sign-in
- onboarding initialization for both email and Google paths
- refresh-token based session renewal
- email ownership verification
- change of password
- change of email with re-verification
- account PIN creation
- onboarding completion after first expense creation

## Authentication Rules

Supported auth paths:

- email sign up
- email login
- Google login / sign up
- refresh token rotation
- logout / token revocation
- email verification
- resend verification
- change password
- change email
- create PIN

Auth response contract notes:

- register may return a `verification_code` in debug mode
- verification is required before standard email login succeeds
- Google auth returns active verified users because Google email verification is trusted
- `AuthUserResponse` includes `onboarding_completed` and `has_pin`

Google auth implementation note:

- the current backend uses Google ID token verification
- in this model, the client signs the user in with Google and sends the Google-issued `id_token` to the backend
- the backend verifies that token against the configured `GOOGLE_CLIENT_ID`
- this flow does not require a `GOOGLE_CLIENT_SECRET`
- a `GOOGLE_CLIENT_SECRET` becomes necessary only if the backend is performing OAuth code exchange itself, such as exchanging an authorization code for Google tokens on a server-side redirect flow

Google account linking rules:

- resolve by `provider_subject` first
- fall back to verified email only when appropriate
- never silently merge unrelated Google identities
- do not trust raw frontend profile data without token verification
- `provider_subject` is a durable account-linking field and should be preserved carefully

Email verification implementation note:

- use a 6-digit verification code
- never store the raw verification code in the database
- store a derived hash of the code scoped to email and verification purpose
- send the verification email asynchronously through Brevo SMTP
- enforce resend cooldowns and max verification attempts
- support both signup verification and change-email verification
- background email sending should never crash a request after the HTTP response has started
- if email delivery is not configured:
  - debug mode may still allow local flow testing via returned verification code
  - non-debug mode should fail cleanly before pretending delivery succeeded

Brevo SMTP assumptions:

- host: `smtp-relay.brevo.com`
- port `587` for STARTTLS
- port `465` for SSL
- login is the SMTP login
- password is the SMTP key
- this backend currently uses SMTP, not Brevo API HTTP endpoints

Important auth constraints:

- email sign up creates onboarding progress immediately
- Google sign up/login also creates onboarding progress if missing
- refresh tokens must be persisted and revocable
- Google identity should be linked by provider subject first, not only email
- email changes should clear Google subject linkage until the new email is re-verified if the old linkage is no longer trustworthy
- PIN creation is protected by password confirmation
- email normalization should be consistent across registration, login, verification, resend, and change-email
- password and PIN hashing are CPU-bound and should not block the async event loop
- first-expense onboarding completion should happen through the expense write path, not through a fake onboarding shortcut

## Verification Data Model Semantics

`email_verification_codes` should be understood as a verification ledger, not a throwaway helper table.

Important fields:

- `user_id`
- `purpose`
- `sent_to_email`
- `code_hash`
- `expires_at`
- `consumed_at`
- `last_sent_at`
- `attempt_count`

Behavioral rules:

- one user can have multiple historical verification records
- active verification should be invalidated when a newer code is issued for the same user/purpose
- cross-user collisions on a pending target email should be prevented
- attempts should be counted on verification checks
- raw code must never be stored
- verification code lookup should be indexed for hot auth paths

## Data Model Expectations

Important entities:

- `users`
- `user_sessions`
- `refresh_tokens`
- `email_verification_codes`
- `onboarding_progress`
- `user_goals`
- `expense_categories`
- `expenses`
- `budgets`
- `savings_goals`
- `savings_contributions`
- `learning_categories`
- `learning_content`
- `content_bookmarks`
- `notification_preferences`
- `faq_categories`
- `faq_items`
- `support_messages`

Onboarding-specific persistence:

- `user_goals`
  - stores the primary first-time goal
- `budgets`
  - stores the first monthly budget
- `expense_categories`
  - stores materialized user categories selected during onboarding
- `expenses`
  - first expense write completes the current onboarding implementation
- `onboarding_progress`
  - drives step progression and completion state

Important schema-specific notes:

- `users.provider_subject` is used for durable external identity linkage
- `refresh_tokens.token` must stay unique
- `onboarding_progress.user_id` is unique
- `expense_categories` may be shared defaults or user-owned records
- notification preferences are unique by user and notification type
- enum-backed fields matter in PostgreSQL migration behavior and must be treated carefully

## Performance And Quality Guardrails

Use these rules for every subsequent feature:

- prefer async DB and IO paths only
- avoid blocking network calls in the event loop
- use shared HTTP clients or provider transports where possible
- avoid unnecessary extra queries on hot auth paths
- preserve indexes on frequent lookup columns like email, provider subject, refresh token, and verification-code lookup fields
- never load large collections when paginated reads are enough
- keep route handlers thin and put logic in services
- add migrations for schema changes instead of relying on `create_all`
- do not introduce N+1 query patterns for dashboard, expenses, learning, or support lists
- select only the fields needed for response DTOs on read-heavy endpoints
- move external side effects like email sending, notifications, and long-running sync work to background jobs when implemented
- avoid doing SMTP, Google verification, bcrypt work, or other slow work directly on the event loop
- prefer one DB round trip over several if the endpoint is on a hot path like register, login, refresh, or dashboard
- be deliberate with indexes for tables involved in authentication and verification

Latency-sensitive paths in this product:

- register
- login
- token refresh
- verify-email
- resend-verification
- dashboard summary
- expense creation

For those paths, another agent should assume:

- avoid unnecessary ORM object loading
- avoid synchronous provider calls unless wrapped or offloaded
- avoid debug-only logic leaking into production behavior
- background work is acceptable, but response semantics must remain accurate
- onboarding-completing expense creation should stay efficient because it is part of first-session activation

## Security Expectations

- never trust client-supplied identity without verification
- always verify Google ID tokens against the configured client ID
- never store plain-text passwords or PINs
- require current-password confirmation for sensitive account mutations
- keep verification and revocation flows explicit
- do not silently merge unrelated user accounts
- never return secrets, SMTP keys, provider subjects, or raw verification artifacts in normal production responses
- treat email ownership changes as sensitive account mutations
- prefer explicit failure over ambiguous fallback when identity linkage looks inconsistent

## Migration Rules

- every schema change must have an Alembic migration
- prefer additive migrations first
- if a field is needed for auth or identity linking, index it
- keep the initial onboarding and auth tables stable

PostgreSQL-specific caution:

- enum types can survive partially failed migration attempts
- `0001` has historically been sensitive around enum creation
- if a migration fails partway in Postgres, inspect:
  - `alembic_version`
  - existing tables
  - existing enum types
  - partially created indexes
- do not assume rerunning `alembic upgrade head` is safe after a failed enum migration without checking state

Practical migration guidance:

- for development SQLite, resetting the DB file is often the fastest recovery path
- for PostgreSQL dev/staging, be careful with partial migration state before retrying
- if a migration is already applied in one environment, prefer a follow-up migration over rewriting historical behavior unless the environment is still disposable

## Known Operational Gotchas

Issues encountered during current buildout:

- route and service signatures can drift when auth flow changes rapidly
- background tasks raising `HTTPException` after a response starts can crash request handling
- Postgres `sslmode` style URLs need normalization for `asyncpg`
- Postgres enum creation can fail on reruns if a partial prior attempt left types behind
- dev and production DB concerns must remain separate because SQLite and PostgreSQL behave differently around DDL and datetimes
- Docker runtime should stay isolated from non-Docker local DB settings

When another agent debugs a failure, likely hotspots are:

- `app/core/config.py`
- `app/db/session.py`
- `alembic/env.py`
- `alembic/versions/0001_initial_schema.py`
- `app/services/auth.py`
- `app/services/onboarding.py`
- `app/services/expenses.py`
- `app/integrations/email.py`
- `app/integrations/google_identity.py`
- `docker-compose.yml`
- `Dockerfile`

## Coding Guidance For Future Work

- preserve backward compatibility of auth response contracts when possible
- if a feature affects onboarding, check both email and Google entry paths
- if a feature touches dashboard latency, optimize read queries before adding UI-driven convenience joins
- if a feature touches money movement or savings calculations, make updates atomic
- if a feature introduces a third-party integration, keep verification off the main event loop

Additional guidance for another agent:

- before changing auth, read the current route contracts and service signatures together
- before editing migrations, inspect whether the target DB is SQLite or PostgreSQL
- before changing email verification behavior, check register, verify-email, resend-verification, and change-email together
- before changing onboarding, check goal selection, first budget, category setup, and first expense completion together
- if introducing a new provider, put it under `app/integrations`
- if changing settings behavior, keep runtime and Alembic resolution in sync
- if adding new response fields, think about debug-vs-production behavior explicitly

## Suggested Next Work Areas

High-value follow-up items:

- add password reset via Brevo
- add PIN reset / rotation flows
- add more complete onboarding completion updates
- add a dedicated onboarding success/readiness endpoint if the mobile app needs a final confirmation screen contract
- add auth integration tests
- add migration smoke tests for SQLite and PostgreSQL
- add Docker smoke tests or startup checks
- add structured logging around auth and email delivery
- add rate limiting or abuse protection for auth endpoints

## Current Operational Notes

- this repo may run locally with SQLite async for development
- the architecture should stay Postgres-ready
- Python runtime was not available in the current execution environment during scaffolding, so runtime verification should always be done locally after major changes
- if working on production-facing features, assume local success on SQLite is not enough; verify PostgreSQL behavior too
