import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Record(Base):
    __tablename__ = "records"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archive_data.pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_id_end: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archive_data.pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aircraft_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    werknummer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incident_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incident_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    damage_percentage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    bounding_boxes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1024), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    page: Mapped["Page"] = relationship(  # noqa: F821
        "Page", back_populates="records", foreign_keys=[page_id]
    )
    personnel: Mapped[list["Personnel"]] = relationship(  # noqa: F821
        "Personnel", back_populates="record", cascade="all, delete-orphan"
    )
    corrections: Mapped[list["RecordCorrection"]] = relationship(  # noqa: F821
        "RecordCorrection", back_populates="record", cascade="all, delete-orphan"
    )
