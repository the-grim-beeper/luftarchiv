"""
Export service for Luftarchiv.

Provides export_records_to_csv() which flattens records + their personnel
into CSV rows with dynamic personnel columns (person_1_rank, person_1_surname, …).
"""

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Collection, Page, Record


RECORD_FIELDS = [
    "id",
    "date",
    "unit_designation",
    "aircraft_type",
    "werknummer",
    "incident_type",
    "incident_description",
    "damage_percentage",
    "location",
    "entry_number",
    "page_id",
    "created_at",
]

PERSONNEL_FIELDS = [
    "rank_abbreviation",
    "rank_full",
    "surname",
    "first_name",
    "fate",
    "fate_english",
]


async def export_records_to_csv(
    collection_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[str, str]:
    """
    Export all records for a collection as CSV.

    Returns (csv_string, filename).
    The CSV has one row per record; personnel data is spread into
    person_1_rank, person_1_surname … person_N_fate columns.
    """
    # Verify collection exists
    collection = await session.get(Collection, collection_id)
    if not collection:
        raise ValueError(f"Collection {collection_id} not found")

    # Fetch all records via pages
    result = await session.execute(
        select(Record)
        .join(Page, Record.page_id == Page.id)
        .where(Page.collection_id == collection_id)
        .options(selectinload(Record.personnel))
        .order_by(Page.page_number, Record.entry_number)
    )
    records = result.scalars().all()

    # Cap personnel columns at 6 (covers 99%+ of records)
    MAX_PERSONNEL_COLS = 6
    actual_max = max((len(r.personnel) for r in records), default=0)
    max_personnel = min(actual_max, MAX_PERSONNEL_COLS)

    # Build header
    header = list(RECORD_FIELDS)
    for i in range(1, max_personnel + 1):
        for field in PERSONNEL_FIELDS:
            header.append(f"person_{i}_{field}")
    if actual_max > MAX_PERSONNEL_COLS:
        header.append("additional_personnel")

    output = io.StringIO()
    writer = csv.writer(output)

    # Provenance header for academic use
    from sqlalchemy import func
    total_pages = (await session.execute(
        select(func.count(Page.id)).where(Page.collection_id == collection_id)
    )).scalar()
    extracted_pages = (await session.execute(
        select(func.count(Page.id)).where(
            Page.collection_id == collection_id,
            Page.ocr_status == "claude_extracted",
        )
    )).scalar()

    writer.writerow([f"# Luftarchiv Export — {collection.name}"])
    writer.writerow([f"# Source Reference: {collection.source_reference or 'N/A'}"])
    writer.writerow([f"# Pages: {extracted_pages}/{total_pages} extracted"])
    writer.writerow([f"# Records: {len(records)}"])
    writer.writerow([f"# Status: {'COMPLETE' if extracted_pages == total_pages else 'PARTIAL'}"])
    writer.writerow([f"# Exported: {datetime.now(timezone.utc).isoformat()}"])
    writer.writerow([])

    writer.writerow(header)

    for record in records:
        row: list = [str(getattr(record, f, "") or "") for f in RECORD_FIELDS]

        # Personnel columns (capped to max_personnel)
        for i, person in enumerate(record.personnel[:max_personnel]):
            for field in PERSONNEL_FIELDS:
                row.append(str(getattr(person, field, "") or ""))
        # Pad remaining personnel slots
        remaining = max_personnel - min(len(record.personnel), max_personnel)
        row.extend([""] * remaining * len(PERSONNEL_FIELDS))

        # Overflow personnel as semicolon-separated string
        if actual_max > MAX_PERSONNEL_COLS:
            overflow = record.personnel[MAX_PERSONNEL_COLS:]
            if overflow:
                parts = [f"{getattr(p, 'rank_abbreviation', '')} {getattr(p, 'surname', '')} ({getattr(p, 'fate_english', '')})" for p in overflow]
                row.append("; ".join(parts))
            else:
                row.append("")

        writer.writerow(row)

    csv_string = output.getvalue()
    safe_name = collection.name.replace(" ", "_").replace("/", "-")
    filename = f"luftarchiv_{safe_name}_{collection_id}.csv"
    return csv_string, filename
