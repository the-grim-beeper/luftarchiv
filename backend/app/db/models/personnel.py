import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Personnel(Base):
    __tablename__ = "personnel"
    __table_args__ = {"schema": "archive_data"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("archive_data.records.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank_abbreviation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rank_full: Mapped[str | None] = mapped_column(String(255), nullable=True)
    surname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fate: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fate_english: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    record: Mapped["Record"] = relationship(  # noqa: F821
        "Record", back_populates="personnel"
    )
