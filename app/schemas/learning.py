from pydantic import BaseModel, Field

from app.models.learning import LearningContentStatus


class LearningCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)


class LearningCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str


class LearningContentCreateRequest(BaseModel):
    category_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1)
    cover_image_url: str | None = Field(default=None, max_length=500)
    content_type: str = Field(default="article", pattern="^(article|video|podcast|series|glossary)$")
    media_url: str | None = Field(default=None, max_length=500)
    media_public_id: str | None = Field(default=None, max_length=255)
    media_resource_type: str | None = Field(default=None, max_length=32)
    status: LearningContentStatus = LearningContentStatus.draft


class LearningContentUpdateRequest(BaseModel):
    category_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    cover_image_url: str | None = Field(default=None, max_length=500)
    content_type: str | None = Field(default=None, pattern="^(article|video|podcast|series|glossary)$")
    media_url: str | None = Field(default=None, max_length=500)
    media_public_id: str | None = Field(default=None, max_length=255)
    media_resource_type: str | None = Field(default=None, max_length=32)
    status: LearningContentStatus | None = None


class LearningContentResponse(BaseModel):
    id: str
    category_id: str | None = None
    created_by: str | None = None
    title: str
    summary: str | None = None
    body: str
    cover_image_url: str | None = None
    content_type: str
    media_url: str | None = None
    media_public_id: str | None = None
    media_resource_type: str | None = None
    status: LearningContentStatus
    view_count: int


class LearningAssetUploadResponse(BaseModel):
    url: str
    public_id: str
    resource_type: str
