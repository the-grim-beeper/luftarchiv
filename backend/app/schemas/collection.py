import uuid
from datetime import datetime

from pydantic import BaseModel


class CollectionCreate(BaseModel):
    name: str
    source_reference: str | None = None
    description: str | None = None
    document_type: str | None = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_reference: str | None
    description: str | None
    document_type: str | None
    page_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CollectionList(BaseModel):
    collections: list[CollectionResponse]
    total: int
