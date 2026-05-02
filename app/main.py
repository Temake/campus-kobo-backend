from contextlib import asynccontextmanager
from typing import Any, Annotated

from fastapi import Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.api.deps import get_current_user_id
from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import init_db


def create_app() -> FastAPI:
    print(f"Starting {settings.app_name} in {settings.app_env} environment. Debug mode is {'on' if settings.app_debug else 'off'}.")
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        description="Backend architecture scaffold for the CampusKobo finance app.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_spec(_user_id: Annotated[str, Depends(get_current_user_id)]) -> dict[str, Any]:
        return app.openapi()

    @app.get("/docs", include_in_schema=False)
    def swagger_ui(_user_id: Annotated[str, Depends(get_current_user_id)]) -> HTMLResponse:
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{settings.app_name} - Docs")

    @app.get("/redoc", include_in_schema=False)
    def redoc_ui(_user_id: Annotated[str, Depends(get_current_user_id)]) -> HTMLResponse:
        return get_redoc_html(openapi_url="/openapi.json", title=f"{settings.app_name} - ReDoc")
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
