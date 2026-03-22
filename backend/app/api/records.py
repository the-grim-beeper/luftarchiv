import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_session
from app.db.models import Record, RecordCorrection
from app.schemas.search import RecordResult

router = APIRouter(prefix="/api/records", tags=["records"])


class CorrectionRequest(BaseModel):
    field_name: str
    corrected_value: str | None = None


class CorrectionResponse(BaseModel):
    id: uuid.UUID
    record_id: uuid.UUID
    field_name: str
    original_value: str | None
    corrected_value: str | None

    model_config = {"from_attributes": True}


@router.get("/{record_id}", response_model=RecordResult)
async def get_record(
    record_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Record)
        .options(selectinload(Record.personnel))
        .where(Record.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.post("/{record_id}/correct", response_model=CorrectionResponse, status_code=201)
async def correct_record(
    record_id: uuid.UUID,
    data: CorrectionRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Record).where(Record.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Validate that the field exists on Record
    correctable_fields = {
        "date", "unit_designation", "aircraft_type", "werknummer",
        "incident_type", "incident_description", "damage_percentage", "location",
    }
    if data.field_name not in correctable_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Field '{data.field_name}' is not correctable. "
                   f"Allowed: {sorted(correctable_fields)}",
        )

    original_value = str(getattr(record, data.field_name, None))

    # Save the correction record
    correction = RecordCorrection(
        record_id=record_id,
        field_name=data.field_name,
        original_value=original_value,
        corrected_value=data.corrected_value,
    )
    session.add(correction)

    # Apply the correction to the record
    setattr(record, data.field_name, data.corrected_value)

    await session.commit()
    await session.refresh(correction)
    return correction
