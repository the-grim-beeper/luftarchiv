import uuid
from datetime import datetime

from pydantic import BaseModel


# --- Glossary ---

class GlossaryCreate(BaseModel):
    term: str
    definition: str | None = None
    category: str | None = None
    language: str | None = "de"
    trust_level: str = "ai_suggested"
    source: str | None = None


class GlossaryResponse(BaseModel):
    id: uuid.UUID
    term: str
    definition: str | None
    category: str | None
    language: str | None
    trust_level: str
    source: str | None
    proposed_by: uuid.UUID | None
    verified_by: uuid.UUID | None
    verified_at: datetime | None

    model_config = {"from_attributes": True}


class GlossaryList(BaseModel):
    items: list[GlossaryResponse]
    total: int


class ReviewAction(BaseModel):
    action: str  # "approve" | "reject" | "demote"
    reason: str | None = None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    old_trust_level: str | None
    new_trust_level: str | None
    reviewer: uuid.UUID | None
    reason: str | None
    reviewed_at: datetime

    model_config = {"from_attributes": True}


# --- Unit Designations ---

class UnitCreate(BaseModel):
    abbreviation: str
    full_name: str | None = None
    unit_type: str | None = None
    notes: str | None = None
    trust_level: str = "ai_suggested"


class UnitResponse(BaseModel):
    id: uuid.UUID
    abbreviation: str
    full_name: str | None
    unit_type: str | None
    notes: str | None
    trust_level: str

    model_config = {"from_attributes": True}


class UnitList(BaseModel):
    items: list[UnitResponse]
    total: int


# --- Aircraft Types ---

class AircraftCreate(BaseModel):
    designation: str
    manufacturer: str | None = None
    common_name: str | None = None
    variants: list[str] | None = None
    trust_level: str = "ai_suggested"


class AircraftResponse(BaseModel):
    id: uuid.UUID
    designation: str
    manufacturer: str | None
    common_name: str | None
    variants: list | None
    trust_level: str

    model_config = {"from_attributes": True}


class AircraftList(BaseModel):
    items: list[AircraftResponse]
    total: int
