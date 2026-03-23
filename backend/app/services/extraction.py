import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import SessionLocal
from app.db.models import Collection, Glossary, Page, PipelineJob, Record, Personnel


async def _get_glossary_context(session: AsyncSession) -> dict[str, str]:
    """Load verified and proposed glossary entries as context for Claude."""
    result = await session.execute(
        select(Glossary).where(Glossary.trust_level.in_(["verified", "proposed"]))
    )
    entries = result.scalars().all()
    return {e.term: e.definition for e in entries}


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
    """Run Claude extraction on all pages with Kraken text."""
    from app.services.ocr_claude import extract_records_from_page

    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    glossary_context = await _get_glossary_context(session)

    result = await session.execute(
        select(Page)
        .where(Page.collection_id == collection_id, Page.ocr_status.in_(["extracted", "pending"]))
        .order_by(Page.page_number)
    )
    pages = result.scalars().all()

    for page in pages:
        try:
            records_data = await extract_records_from_page(
                image_path=page.image_path,
                raw_ocr_text=page.raw_ocr_text or "",
                glossary_context=glossary_context,
            )

            for rec_data in records_data:
                personnel_data = rec_data.pop("personnel", [])
                new_abbrevs = rec_data.pop("new_abbreviations", [])

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


async def run_embedding_stage(session: AsyncSession, collection_id: uuid.UUID, job_id: uuid.UUID):
    """Generate search embeddings for all records in a collection."""
    from app.services.embeddings import generate_record_summary, generate_embedding

    job = await session.get(PipelineJob, job_id)
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    result = await session.execute(
        select(Record)
        .join(Record.page)
        .where(Page.collection_id == collection_id, Record.search_embedding.is_(None))
        .options(selectinload(Record.personnel))
    )
    records = result.scalars().all()

    for record in records:
        try:
            summary = generate_record_summary(record)
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


# Background task wrappers — create their own sessions (Fix 1)
async def run_kraken_stage_background(collection_id: uuid.UUID, job_id: uuid.UUID):
    async with SessionLocal() as session:
        await run_kraken_stage(session, collection_id, job_id)


async def run_claude_stage_background(collection_id: uuid.UUID, job_id: uuid.UUID):
    async with SessionLocal() as session:
        await run_claude_stage(session, collection_id, job_id)


async def run_embedding_stage_background(collection_id: uuid.UUID, job_id: uuid.UUID):
    async with SessionLocal() as session:
        await run_embedding_stage(session, collection_id, job_id)
