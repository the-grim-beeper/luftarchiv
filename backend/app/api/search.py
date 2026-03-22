from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.search import SearchFilters, SearchResponse
from app.services.search import analytical_search, direct_search, semantic_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_records(
    filters: SearchFilters,
    session: AsyncSession = Depends(get_session),
):
    if filters.mode == "semantic":
        records = await semantic_search(filters, session)
        return SearchResponse(records=records, total=len(records), mode="semantic")

    if filters.mode == "analytical":
        records, synthesis = await analytical_search(filters, session)
        return SearchResponse(
            records=records, total=len(records), mode="analytical", synthesis=synthesis
        )

    # Default: direct
    records = await direct_search(filters, session)
    return SearchResponse(records=records, total=len(records), mode="direct")
