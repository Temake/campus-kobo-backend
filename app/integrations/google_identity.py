import requests
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings

_http_session = requests.Session()
_google_request = google_requests.Request(session=_http_session)


async def verify_google_id_token(token: str) -> dict:
    return await run_in_threadpool(_verify_google_id_token_sync, token)


def _verify_google_id_token_sync(token: str) -> dict:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication is not configured",
        )

    try:
        payload = id_token.verify_oauth2_token(token, _google_request, settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google identity token") from exc

    issuer = payload.get("iss")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token issuer")
    if not payload.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account email is not verified")
    if not payload.get("email"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account email is missing")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account identifier is missing")

    return payload
