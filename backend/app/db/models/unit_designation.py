import uuid

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UnitDesignation(Base):
    __tablename__ = "unit_designations"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    abbreviation: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    unit_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parent_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archive_knowledge.unit_designations.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_from: Mapped[str | None] = mapped_column(Date, nullable=True)
    active_to: Mapped[str | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False, default="ai_suggested")

    # Relationships
    parent_unit: Mapped["UnitDesignation | None"] = relationship(
        "UnitDesignation",
        back_populates="child_units",
        foreign_keys=[parent_unit_id],
        remote_side="UnitDesignation.id",
    )
    child_units: Mapped[list["UnitDesignation"]] = relationship(
        "UnitDesignation",
        back_populates="parent_unit",
        foreign_keys=[parent_unit_id],
    )
