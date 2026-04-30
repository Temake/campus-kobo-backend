from fastapi import HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings


class CloudinaryStorageService:
    def is_configured(self) -> bool:
        return bool(settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret)

    async def upload_avatar(self, file: UploadFile) -> dict[str, str]:
        return await self._upload(file, folder="campuskobo/avatars")

    async def upload_learning_asset(self, file: UploadFile) -> dict[str, str]:
        return await self._upload(file, folder="campuskobo/learning")

    async def _upload(self, file: UploadFile, folder: str) -> dict[str, str]:
        if not self.is_configured():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloudinary is not configured")

        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloudinary SDK is not installed") from exc

        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )
        content = await file.read()
        result = await run_in_threadpool(
            cloudinary.uploader.upload,
            content,
            folder=folder,
            resource_type="auto",
        )
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "resource_type": result.get("resource_type", "image"),
        }
