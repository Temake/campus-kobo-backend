# CampusKobo Backend

FastAPI backend architecture scaffolded from the CampusKobo mobile UI flows in Figma.

## What is included

- FastAPI application factory and router registration
- Async SQLAlchemy 2.0 engine and session management
- SQLAlchemy 2.0 models for auth, onboarding, money tracking, learning, support, and settings
- Pydantic request and response schemas
- JWT-based authentication flow with persisted users, verification codes, refresh tokens, password change, email change, and PIN creation
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

## Suggested next steps

1. Wire verification emails and PIN reset delivery through a real provider.
2. Add Redis for refresh token/session revocation and notification jobs.
3. Replace placeholder domain services with real queries and pagination.
4. Add tests for auth, expense creation, budgeting, and onboarding flows.
