from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Page, Record
from app.schemas.search import RecordResult, SearchFilters, SearchResponse
from app.services.search import analytical_search, direct_search, semantic_search

router = APIRouter(prefix="/api/search", tags=["search"])


def _enrich_record(record: Record, page_map: dict) -> dict:
    """Add page_id, collection_id, page_number to a record result."""
    data = {
        "id": record.id,
        "date": record.date,
        "unit_designation": record.unit_designation,
        "aircraft_type": record.aircraft_type,
        "werknummer": record.werknummer,
        "incident_type": record.incident_type,
        "incident_description": record.incident_description,
        "damage_percentage": record.damage_percentage,
        "location": record.location,
        "entry_number": record.entry_number,
        "page_id": record.page_id,
        "personnel": record.personnel,
        "created_at": record.created_at,
    }
    page_info = page_map.get(record.page_id)
    if page_info:
        data["collection_id"] = page_info["collection_id"]
        data["page_number"] = page_info["page_number"]
    return data


async def _get_page_map(session: AsyncSession, page_ids: set) -> dict:
    """Fetch page info for a set of page IDs."""
    if not page_ids:
        return {}
    result = await session.execute(
        select(Page.id, Page.collection_id, Page.page_number)
        .where(Page.id.in_(page_ids))
    )
    return {
        row[0]: {"collection_id": row[1], "page_number": row[2]}
        for row in result.fetchall()
    }


@router.post("", response_model=SearchResponse)
async def search_records(
    filters: SearchFilters,
    session: AsyncSession = Depends(get_session),
):
    if filters.mode == "semantic":
        records = await semantic_search(filters, session)
    elif filters.mode == "analytical":
        records, synthesis = await analytical_search(filters, session)
        page_map = await _get_page_map(session, {r.page_id for r in records})
        enriched = [_enrich_record(r, page_map) for r in records]
        return SearchResponse(
            records=enriched, total=len(records), mode="analytical", synthesis=synthesis
        )
    else:
        records = await direct_search(filters, session)

    # Get total count (without limit) for pagination
    total = len(records)  # For now, use result count; could add a count query later

    page_map = await _get_page_map(session, {r.page_id for r in records})
    enriched = [_enrich_record(r, page_map) for r in records]

    return SearchResponse(records=enriched, total=total, mode=filters.mode)
