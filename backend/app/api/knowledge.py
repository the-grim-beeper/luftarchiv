import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import AircraftType, Glossary, KnowledgeReview, UnitDesignation
from app.schemas.knowledge import (
    AircraftCreate,
    AircraftList,
    AircraftResponse,
    GlossaryCreate,
    GlossaryList,
    GlossaryResponse,
    ReviewAction,
    ReviewResponse,
    UnitCreate,
    UnitList,
    UnitResponse,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

ADMIN_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Trust level constants
TRUST_VERIFIED = 2
TRUST_UNVERIFIED = 1
TRUST_REJECTED = -1


# --- Glossary endpoints ---

@router.get("/glossary", response_model=GlossaryList)
async def list_glossary(
    trust_level: int | None = Query(None, description="Filter by trust level"),
    category: str | None = Query(None, description="Filter by category"),
    session: AsyncSession = Depends(get_session),
):
    query = select(Glossary)
    if trust_level is not None:
        query = query.where(Glossary.trust_level == trust_level)
    if category is not None:
        query = query.where(Glossary.category == category)
    query = query.order_by(Glossary.term)

    result = await session.execute(query)
    items = result.scalars().all()

    count_query = select(func.count(Glossary.id))
    if trust_level is not None:
        count_query = count_query.where(Glossary.trust_level == trust_level)
    if category is not None:
        count_query = count_query.where(Glossary.category == category)
    count_result = await session.execute(count_query)
    total = count_result.scalar()

    return GlossaryList(items=items, total=total)


@router.post("/glossary", response_model=GlossaryResponse, status_code=201)
async def create_glossary_entry(
    data: GlossaryCreate,
    session: AsyncSession = Depends(get_session),
):
    entry = Glossary(**data.model_dump())
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.post("/glossary/{entry_id}/review", response_model=ReviewResponse)
async def review_glossary_entry(
    entry_id: uuid.UUID,
    action: ReviewAction,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Glossary).where(Glossary.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary entry not found")

    if action.action not in ("approve", "reject", "demote"):
        raise HTTPException(
            status_code=400,
            detail="action must be one of: approve, reject, demote",
        )

    old_trust = entry.trust_level

    if action.action == "approve":
        entry.trust_level = TRUST_VERIFIED
        entry.verified_by = ADMIN_UUID
        entry.verified_at = datetime.now(timezone.utc)
        new_trust = TRUST_VERIFIED
    elif action.action == "reject":
        entry.trust_level = TRUST_REJECTED
        new_trust = TRUST_REJECTED
    else:  # demote
        entry.trust_level = TRUST_UNVERIFIED
        new_trust = TRUST_UNVERIFIED

    review = KnowledgeReview(
        entity_type="glossary",
        entity_id=entry_id,
        action=action.action,
        old_trust_level=old_trust,
        new_trust_level=new_trust,
        reviewer=ADMIN_UUID,
        reason=action.reason,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


# --- Unit Designation endpoints ---

@router.get("/units", response_model=UnitList)
async def list_units(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(UnitDesignation).order_by(UnitDesignation.abbreviation))
    items = result.scalars().all()
    count_result = await session.execute(select(func.count(UnitDesignation.id)))
    total = count_result.scalar()
    return UnitList(items=items, total=total)


@router.post("/units", response_model=UnitResponse, status_code=201)
async def create_unit(
    data: UnitCreate,
    session: AsyncSession = Depends(get_session),
):
    unit = UnitDesignation(**data.model_dump())
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


# --- Aircraft Type endpoints ---

@router.get("/aircraft", response_model=AircraftList)
async def list_aircraft(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(AircraftType).order_by(AircraftType.designation))
    items = result.scalars().all()
    count_result = await session.execute(select(func.count(AircraftType.id)))
    total = count_result.scalar()
    return AircraftList(items=items, total=total)


@router.post("/aircraft", response_model=AircraftResponse, status_code=201)
async def create_aircraft(
    data: AircraftCreate,
    session: AsyncSession = Depends(get_session),
):
    aircraft = AircraftType(**data.model_dump())
    session.add(aircraft)
    await session.commit()
    await session.refresh(aircraft)
    return aircraft
