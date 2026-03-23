import uuid

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AircraftType(Base):
    __tablename__ = "aircraft_types"
    __table_args__ = {"schema": "archive_knowledge"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    common_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variants: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False, default="ai_suggested")
