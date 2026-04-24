from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id
from app.schemas.user import UserProfileResponse

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user_id: Annotated[str, Depends(get_current_user_id)]) -> UserProfileResponse:
    # Replace with a proper read service or repository query.
    return UserProfileResponse(
        id=current_user_id,
        email="student@example.com",
        phone_number=None,
        full_name="Campus Kobo User",
        has_pin=False,
        biometric_enabled=False,
    )
