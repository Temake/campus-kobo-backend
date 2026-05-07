from pydantic import BaseModel, EmailStr, Field


class FAQCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)


class FAQCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str


class FAQItemCreateRequest(BaseModel):
    category_id: str | None = None
    question: str = Field(min_length=1, max_length=255)
    answer: str = Field(min_length=1)
    is_published: bool = True


class FAQItemUpdateRequest(BaseModel):
    category_id: str | None = None
    question: str | None = Field(default=None, min_length=1, max_length=255)
    answer: str | None = Field(default=None, min_length=1)
    is_published: bool | None = None


class FAQItemResponse(BaseModel):
    id: str
    category_id: str | None = None
    category: FAQCategoryResponse | None = None
    question: str
    answer: str
    is_published: bool


class SupportMessageCreateRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str = "Support request"
    message: str


class SupportMessageResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    subject: str
    message: str
    status: str
