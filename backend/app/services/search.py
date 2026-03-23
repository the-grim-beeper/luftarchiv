"""
Search service for Luftarchiv.

Three modes:
- direct_search()     — SQL ILIKE filters
- semantic_search()   — pgvector cosine distance on search_embedding
- analytical_search() — Claude synthesis over semantic+direct candidates
"""

import re
import uuid

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Record
from app.schemas.search import SearchFilters


async def direct_search(
    filters: SearchFilters,
    session: AsyncSession,
) -> list[Record]:
    query = select(Record).options(selectinload(Record.personnel))

    conditions = []

    if filters.unit:
        conditions.append(Record.unit_designation.ilike(f"%{filters.unit}%"))
    if filters.aircraft_type:
        conditions.append(Record.aircraft_type.ilike(f"%{filters.aircraft_type}%"))
    if filters.incident_type:
        conditions.append(Record.incident_type.ilike(f"%{filters.incident_type}%"))
    if filters.date_from:
        conditions.append(Record.date >= filters.date_from)
    if filters.date_to:
        conditions.append(Record.date <= filters.date_to)
    free_text = filters.free_text or filters.query
    if free_text:
        ft = f"%{free_text}%"
        conditions.append(
            or_(
                Record.unit_designation.ilike(ft),
                Record.aircraft_type.ilike(ft),
                Record.incident_type.ilike(ft),
                Record.incident_description.ilike(ft),
                Record.raw_text_original.ilike(ft),
                Record.location.ilike(ft),
                Record.werknummer.ilike(ft),
            )
        )

    if filters.personnel_name:
        # Subquery: join via personnel table
        from app.db.models import Personnel

        name_like = f"%{filters.personnel_name}%"
        personnel_subq = (
            select(Personnel.record_id)
            .where(
                or_(
                    Personnel.surname.ilike(name_like),
                    Personnel.first_name.ilike(name_like),
                )
            )
            .scalar_subquery()
        )
        conditions.append(Record.id.in_(personnel_subq))

    if conditions:
        query = query.where(*conditions)

    query = query.order_by(Record.date.desc().nulls_last()).offset(filters.offset).limit(filters.limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def semantic_search(
    filters: SearchFilters,
    session: AsyncSession,
) -> list[Record]:
    from app.services.embeddings import generate_embedding

    query_text = " ".join(
        part
        for part in [
            filters.unit,
            filters.aircraft_type,
            filters.incident_type,
            filters.personnel_name,
            filters.free_text,
        ]
        if part
    )
    if not query_text:
        return []

    embedding = await generate_embedding(query_text)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    # Use pgvector cosine distance operator <=>
    raw = text(
        """
        SELECT id
        FROM archive_data.records
        WHERE search_embedding IS NOT NULL
        ORDER BY search_embedding <=> CAST(:embedding AS vector)
        LIMIT :limit OFFSET :offset
        """
    )
    result = await session.execute(
        raw, {"embedding": embedding_str, "limit": filters.limit, "offset": filters.offset}
    )
    ids = [row[0] for row in result.fetchall()]
    if not ids:
        return []

    records_result = await session.execute(
        select(Record).options(selectinload(Record.personnel)).where(Record.id.in_(ids))
    )
    records_by_id = {r.id: r for r in records_result.scalars().all()}
    # Return in cosine distance order
    return [records_by_id[i] for i in ids if i in records_by_id]


async def analytical_search(
    filters: SearchFilters,
    session: AsyncSession,
) -> tuple[list[Record], str]:
    """
    Combines semantic + direct search to gather candidates, then asks
    Claude to synthesise a response with citation validation.

    Returns (records, synthesis_text).
    """
    import anthropic

    from app.config import settings

    # Gather candidates (more than final limit for Claude to rank)
    expanded = SearchFilters(
        **{**filters.model_dump(), "limit": min(filters.limit * 3, 60), "offset": 0}
    )

    sem_records = await semantic_search(expanded, session)
    dir_records = await direct_search(expanded, session)

    # Merge, deduplicate, preserve order
    seen: set[uuid.UUID] = set()
    candidates: list[Record] = []
    for r in sem_records + dir_records:
        if r.id not in seen:
            seen.add(r.id)
            candidates.append(r)

    if not candidates:
        return [], "No records found matching the search criteria."

    # Build context for Claude
    records_text_parts: list[str] = []
    for rec in candidates:
        pnames = ", ".join(
            " ".join(filter(None, [p.rank_abbreviation, p.surname, p.first_name]))
            for p in rec.personnel
        )
        records_text_parts.append(
            f"[Record {rec.id}]\n"
            f"Date: {rec.date} | Unit: {rec.unit_designation} | Aircraft: {rec.aircraft_type}\n"
            f"Incident: {rec.incident_type} | Location: {rec.location}\n"
            f"Personnel: {pnames or 'none'}\n"
            f"Description: {rec.incident_description or ''}"
        )

    user_query = " | ".join(
        f"{k}: {v}"
        for k, v in filters.model_dump().items()
        if v and k not in ("mode", "limit", "offset")
    )

    context_block = "\n\n---\n\n".join(records_text_parts)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"You are a Luftwaffe archive research assistant. "
                    f"The user is searching for: {user_query}\n\n"
                    f"Here are candidate records from the archive:\n\n{context_block}\n\n"
                    f"Provide a concise analytical synthesis of the relevant findings. "
                    f"Reference specific records using their IDs (e.g. [Record <uuid>]). "
                    f"Only cite records that directly relate to the query."
                ),
            }
        ],
    )
    synthesis = message.content[0].text

    # Citation validation: extract [Record <uuid>] references and verify they exist
    cited_ids_raw = re.findall(
        r"\[Record ([0-9a-f-]{36})\]", synthesis, re.IGNORECASE
    )
    candidate_ids = {r.id for r in candidates}
    valid_cited_ids: set[uuid.UUID] = set()
    for raw_id in cited_ids_raw:
        try:
            uid = uuid.UUID(raw_id)
            if uid in candidate_ids:
                valid_cited_ids.add(uid)
        except ValueError:
            pass

    # Filter returned records to cited ones (preserve candidate order)
    cited_records = [r for r in candidates if r.id in valid_cited_ids]

    # Fall back to all candidates if no citations were validated
    if not cited_records:
        cited_records = candidates[: filters.limit]

    return cited_records[: filters.limit], synthesis
