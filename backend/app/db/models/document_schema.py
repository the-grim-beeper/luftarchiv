import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class DocumentSchema(Base):
    __tablename__ = "document_schemas"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_definitions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Plain UUID — NOT a FK to avoid cross-schema FK issues
    example_collection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False, default="ai_suggested")
