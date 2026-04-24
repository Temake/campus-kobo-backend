from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, get_current_user_id
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard import DashboardService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: DBSession,
) -> DashboardSummaryResponse:
    return await DashboardService(db).get_summary(current_user_id)
