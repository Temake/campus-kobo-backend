from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, get_current_user_id
from app.schemas.dashboard import DashboardResponse, DashboardSummaryResponse
from app.services.dashboard import DashboardService

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> DashboardResponse:
    return await DashboardService(db).get_dashboard(current_user_id)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> DashboardSummaryResponse:
    return await DashboardService(db).get_summary(current_user_id)
