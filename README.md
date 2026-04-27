# CampusKobo Backend

FastAPI backend architecture

## What is included

- FastAPI application factory and router registration
- Async SQLAlchemy 2.0 engine and session management
- SQLAlchemy 2.0 models for auth, onboarding, money tracking, learning, support, and settings
- Pydantic request and response schemas
- JWT-based authentication flow with persisted users, verification codes, refresh tokens, password change, email change, PIN creation, and Google sign-in/sign-up
- Service layer stubs for business logic
- Alembic migration scaffolding with an initial schema revision
- Database schema documentation

## Product domains covered

- Authentication and session management
- User onboarding and profile setup
- Dashboard summaries
- Expenses and categories
- Monthly budgets
- Savings goals and contributions
- Learning hub content and bookmarks
- Notifications and quiet hours
- Security, privacy, PIN, and biometric settings
- FAQ and support contact

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Environment variables

Copy `.env.example` to `.env` and update values.

Database selection:

- `APP_ENV=development` uses `DEVELOPMENT_DATABASE_URL`
- `APP_ENV=production` uses `PRODUCTION_DATABASE_URL` and falls back to `DATABASE_URL` if not set
- `DATABASE_URL` is used as a fallback for non-standard environments

Example:

```env
APP_ENV=development
DEVELOPMENT_DATABASE_URL=sqlite+aiosqlite:///./campuskobo.db
PRODUCTION_DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

## Database initialization

For local bootstrap without migrations:

```bash
python -m app.db.init_db
```

Preferred workflow:

```bash
alembic upgrade head
```

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

## Authentication features

- Email sign up and login
- Google sign up and login via verified Google ID token
- 6-digit email verification and resend verification via Brevo SMTP
- Refresh token rotation and logout
- Change password
- Change email
- Create account PIN

## Suggested next steps

1. Wire verification emails and PIN reset delivery through a real provider.
2. Add Redis for refresh token/session revocation and notification jobs.
3. Replace placeholder domain services with real queries and pagination.
4. Add tests for auth, expense creation, budgeting, and onboarding flows.
