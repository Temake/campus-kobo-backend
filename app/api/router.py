from fastapi import APIRouter

from app.api.routes import auth, budgets, dashboard, expenses, learning, notifications, onboarding, savings, support, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
api_router.include_router(savings.router, prefix="/savings", tags=["savings"])
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
