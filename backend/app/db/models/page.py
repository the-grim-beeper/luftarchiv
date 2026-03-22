import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archive_data.collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ocr_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    segmentation_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    collection: Mapped["Collection"] = relationship(  # noqa: F821
        "Collection", back_populates="pages"
    )
    records: Mapped[list["Record"]] = relationship(  # noqa: F821
        "Record",
        back_populates="page",
        foreign_keys="Record.page_id",
        cascade="all, delete-orphan",
    )
