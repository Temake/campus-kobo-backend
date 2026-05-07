from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.models.learning import LearningContentStatus


class LearningCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    icon_name: str | None = Field(default=None, max_length=100)


class LearningCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    icon_name: str | None = Field(default=None, max_length=100)


class LearningCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    icon_name: str | None = None


class LearningContentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1, validation_alias=AliasChoices("body", "content"))
    cover_image_url: str | None = Field(default=None, max_length=500)
    content_type: str = Field(
        default="article",
        pattern="^(article|video|podcast|series|glossary)$",
        validation_alias=AliasChoices("content_type", "type"),
    )
    media_url: str | None = Field(default=None, max_length=500)
    media_public_id: str | None = Field(default=None, max_length=255)
    media_resource_type: str | None = Field(default=None, max_length=32)
    duration: str | None = Field(default=None, max_length=100)
    key_takeaways: list[str] = Field(default_factory=list)
    related_content_ids: list[str] = Field(default_factory=list)
    episode_number: int | None = None
    is_featured: bool = False
    status: LearningContentStatus = LearningContentStatus.draft


class LearningContentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, min_length=1, validation_alias=AliasChoices("body", "content"))
    cover_image_url: str | None = Field(default=None, max_length=500)
    content_type: str | None = Field(
        default=None,
        pattern="^(article|video|podcast|series|glossary)$",
        validation_alias=AliasChoices("content_type", "type"),
    )
    media_url: str | None = Field(default=None, max_length=500)
    media_public_id: str | None = Field(default=None, max_length=255)
    media_resource_type: str | None = Field(default=None, max_length=32)
    duration: str | None = Field(default=None, max_length=100)
    key_takeaways: list[str] | None = None
    related_content_ids: list[str] | None = None
    episode_number: int | None = None
    is_featured: bool | None = None
    status: LearningContentStatus | None = None


class LearningContentResponse(BaseModel):
    id: str
    category_id: str | None = None
    created_by: str | None = None
    title: str
    summary: str | None = None
    body: str
    content: str
    cover_image_url: str | None = None
    content_type: str
    type: str
    media_url: str | None = None
    media_public_id: str | None = None
    media_resource_type: str | None = None
    duration: str | None = None
    key_takeaways: list[str] = Field(default_factory=list)
    related_content_ids: list[str] = Field(default_factory=list)
    episode_number: int | None = None
    is_featured: bool = False
    status: LearningContentStatus
    view_count: int
    category: LearningCategoryResponse | None = None


class GlossaryTermCreateRequest(BaseModel):
    term: str = Field(min_length=1, max_length=255)
    definition: str = Field(min_length=1)
    part_of_speech: str | None = Field(default="noun", max_length=50)
    example: str | None = None
    related_terms: list[str] = Field(default_factory=list)
    is_term_of_day: bool = False


class GlossaryTermUpdateRequest(BaseModel):
    term: str | None = Field(default=None, min_length=1, max_length=255)
    definition: str | None = Field(default=None, min_length=1)
    part_of_speech: str | None = Field(default=None, max_length=50)
    example: str | None = None
    related_terms: list[str] | None = None
    is_term_of_day: bool | None = None


class GlossaryTermResponse(BaseModel):
    id: str
    term: str
    definition: str
    part_of_speech: str | None = None
    example: str | None = None
    related_terms: list[str] = Field(default_factory=list)
    is_term_of_day: bool


class LearningAssetUploadResponse(BaseModel):
    url: str
    public_id: str
    resource_type: str
