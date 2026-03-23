import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import SessionLocal
from app.db.models import Collection, Glossary, Page, PipelineJob, Record, Personnel


def _parse_date(val: str | None) -> date | None:
    """Parse ISO date string from Claude, return None on failure."""
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


async def _get_glossary_context(session: AsyncSession) -> dict[str, str]:
    """Load verified and proposed glossary entries as context for Claude."""
    result = await session.execute(
        select(Glossary).where(Glossary.trust_level.in_(["verified", "proposed"]))
    )
    entries = result.scalars().all()
    return {e.term: e.definition for e in entries}


async def _pages_with_records(session: AsyncSession, collection_id: uuid.UUID) -> set[uuid.UUID]:
    """Get set of page IDs that already have extracted records (for duplicate prevention)."""
    result = await session.execute(
        select(Record.page_id)
        .join(Page, Record.page_id == Page.id)
        .where(Page.collection_id == collection_id)
        .distinct()
    )
    return {row[0] for row in result.fetchall()}


async def run_kraken_stage(session: AsyncSession, collection_id: uuid.UUID, job_id: uuid.UUID):
    """Run Kraken OCR on all pending pages in a collection."""
    from app.services.ocr_kraken import kraken_ocr_page

    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    result = await session.execute(
        select(Page)
        .where(Page.collection_id == collection_id, Page.ocr_status == "pending")
        .order_by(Page.page_number)
    )
    pages = result.scalars().all()

    for page in pages:
        try:
            ocr_result = await kraken_ocr_page(page.image_path)
            page.raw_ocr_text = ocr_result["raw_text"]
            page.segmentation_data = ocr_result["segmentation"]
            page.ocr_status = "extracted"
            job.processed_pages += 1
            job.last_processed_page_id = page.id
            await session.commit()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed on page {page.page_number}: {str(e)}"
            await session.commit()
            return

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def run_claude_stage(session: AsyncSession, collection_id: uuid.UUID, job_id: uuid.UUID):
    """Run LLM extraction on pages that don't already have records."""
    from app.services.llm_config import load_config

    config = load_config()
    if config.provider == "ollama":
        from app.services.ocr_ollama import extract_records_from_page
    elif config.provider == "none":
        # Skip extraction entirely
        job = await session.get(PipelineJob, job_id)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        return
    else:
        from app.services.ocr_claude import extract_records_from_page

    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    glossary_context = await _get_glossary_context(session)

    # Get pages that already have records — skip them
    already_extracted = await _pages_with_records(session, collection_id)

    result = await session.execute(
        select(Page)
        .where(Page.collection_id == collection_id)
        .order_by(Page.page_number)
    )
    all_pages = result.scalars().all()

    # Filter to only pages without records
    pages_to_process = [p for p in all_pages if p.id not in already_extracted]

    # Update total to reflect actual work
    job.total_pages = len(pages_to_process)
    await session.commit()

    if not pages_to_process:
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        return

    for page in pages_to_process:
        try:
            records_data = await extract_records_from_page(
                image_path=page.image_path,
                raw_ocr_text=page.raw_ocr_text or "",
                glossary_context=glossary_context,
            )

            for rec_data in records_data:
                personnel_data = rec_data.pop("personnel", [])
                new_abbrevs = rec_data.pop("new_abbreviations", [])

                # Parse date string to date object
                if "date" in rec_data and isinstance(rec_data["date"], str):
                    rec_data["date"] = _parse_date(rec_data["date"])

                # Filter to only valid Record columns
                valid_columns = {c.key for c in Record.__table__.columns}
                filtered = {k: v for k, v in rec_data.items() if k in valid_columns}

                record = Record(page_id=page.id, **filtered)
                session.add(record)
                await session.flush()

                for p in personnel_data:
                    person = Personnel(record_id=record.id, **p)
                    session.add(person)

                # Auto-suggest new abbreviations
                for abbrev in new_abbrevs:
                    existing = await session.execute(
                        select(Glossary).where(Glossary.term == abbrev["term"])
                    )
                    if not existing.scalar_one_or_none():
                        glossary_entry = Glossary(
                            term=abbrev["term"],
                            definition=abbrev.get("suggested_definition", ""),
                            category=abbrev.get("category", "other"),
                            trust_level="ai_suggested",
                            source=f"Auto-detected from page {page.page_number}",
                        )
                        session.add(glossary_entry)

            # Mark page as extracted
            page.ocr_status = "claude_extracted"
            job.processed_pages += 1
            job.last_processed_page_id = page.id
            await session.commit()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed on page {page.page_number}: {str(e)}"
            await session.commit()
            return

    # Update collection status
    collection = await session.get(Collection, collection_id)
    if collection:
        # Check if all pages are extracted
        total_pages = (await session.execute(
            select(func.count(Page.id)).where(Page.collection_id == collection_id)
        )).scalar()
        extracted_pages = (await session.execute(
            select(func.count(Page.id)).where(
                Page.collection_id == collection_id,
                Page.ocr_status == "claude_extracted",
            )
        )).scalar()
        if extracted_pages == total_pages:
            collection.status = "complete"

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()


async def run_embedding_stage(session: AsyncSession, collection_id: uuid.UUID, job_id: uuid.UUID):
    """Generate search embeddings for all records in a collection."""
    from app.services.embeddings import generate_record_summary, generate_embedding

    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    glossary = await _get_glossary_context(session)

    result = await session.execute(
        select(Record)
        .join(Page, Record.page_id == Page.id)
        .where(Page.collection_id == collection_id, Record.search_embedding.is_(None))
        .options(selectinload(Record.personnel))
    )
    records = result.scalars().all()

    for record in records:
        try:
            personnel_dicts = [
                {"rank_full": p.rank_full, "surname": p.surname, "fate_english": p.fate_english}
                for p in record.personnel
            ]
            summary = generate_record_summary(
                date=str(record.date) if record.date else None,
                aircraft_type=record.aircraft_type,
                werknummer=record.werknummer,
                unit_designation=record.unit_designation,
                incident_type=record.incident_type,
                damage_percentage=record.damage_percentage,
                location=record.location,
                personnel=personnel_dicts,
                glossary=glossary,
            )
            record.search_embedding = await generate_embedding(summary)
            job.processed_pages += 1
            await session.commit()
        except Exception as e:
            job.status = "failed"
            job.error_message = f"Embedding failed for record {record.id}: {str(e)}"
            await session.commit()
            return

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    await session.commit()


# Background task wrappers — create their own sessions
async def run_kraken_stage_background(collection_id: uuid.UUID, job_id: uuid.UUID):
    async with SessionLocal() as session:
        await run_kraken_stage(session, collection_id, job_id)


async def run_claude_stage_background(collection_id: uuid.UUID, job_id: uuid.UUID):
    async with SessionLocal() as session:
        await run_claude_stage(session, collection_id, job_id)


async def run_embedding_stage_background(collection_id: uuid.UUID, job_id: uuid.UUID):
    async with SessionLocal() as session:
        await run_embedding_stage(session, collection_id, job_id)
