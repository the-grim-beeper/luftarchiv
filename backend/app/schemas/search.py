import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SearchFilters(BaseModel):
    # Direct filters
    unit: str | None = None
    aircraft_type: str | None = None
    incident_type: str | None = None
    date_from: str | None = None  # "YYYY-MM-DD" or partial date string
    date_to: str | None = None
    personnel_name: str | None = None
    free_text: str | None = None
    query: str | None = None  # alias for free_text from frontend

    # Search mode
    mode: str = "direct"  # "direct" | "semantic" | "analytical"

    # Pagination
    limit: int = 50
    offset: int = 0


class PersonnelResult(BaseModel):
    id: uuid.UUID
    rank_abbreviation: str | None
    rank_full: str | None
    surname: str | None
    first_name: str | None
    fate: str | None
    fate_english: str | None

    model_config = {"from_attributes": True}


class RecordResult(BaseModel):
    id: uuid.UUID
    date: date | None
    unit_designation: str | None
    aircraft_type: str | None
    werknummer: str | None
    incident_type: str | None
    incident_description: str | None
    damage_percentage: int | None
    location: str | None
    entry_number: int | None = None
    page_id: uuid.UUID | None = None
    collection_id: uuid.UUID | None = None
    page_number: int | None = None
    personnel: list[PersonnelResult]
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    records: list[RecordResult]
    total: int
    mode: str
    synthesis: str | None = None  # populated for analytical search
