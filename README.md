# CampusKobo Backend

FastAPI backend architecture scaffolded from the CampusKobo mobile UI flows in Figma.

## What is included

- FastAPI application factory and router registration
- SQLAlchemy 2.0 models for auth, onboarding, money tracking, learning, support, and settings
- Pydantic request and response schemas
- JWT-based authentication flow boilerplate
- Service layer stubs for business logic
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
uvicorn app.main:app --reload
```

## Environment variables

Copy `.env.example` to `.env` and update values.

## Suggested next steps

1. Add Alembic migrations.
2. Add async database support if desired.
3. Add Redis for refresh token/session revocation and notification jobs.
4. Wire in actual email and OTP delivery providers.
5. Add tests for auth, expense creation, budgeting, and onboarding flows.
