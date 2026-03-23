import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.database import get_session
from app.db.models import Collection, Page, PipelineJob, Record
from app.schemas.collection import CollectionCreate, CollectionList, CollectionResponse
from app.services.extraction import (
    run_claude_stage_background,
    run_embedding_stage_background,
    run_kraken_stage_background,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=CollectionList)
async def list_collections(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Collection).order_by(Collection.created_at.desc()))
    collections = result.scalars().all()
    return CollectionList(collections=collections, total=len(collections))


@router.post("", response_model=CollectionResponse, status_code=201)
async def create_collection(data: CollectionCreate, session: AsyncSession = Depends(get_session)):
    collection = Collection(**data.model_dump())
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}", status_code=200)
async def delete_collection(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Delete a collection and all associated data (pages, records, personnel, jobs)."""
    from app.db.models import Personnel, RecordCorrection

    collection = await session.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Delete in order: personnel → corrections → records → jobs → pages → collection
    record_ids_result = await session.execute(
        select(Record.id).join(Page, Record.page_id == Page.id).where(Page.collection_id == collection_id)
    )
    record_ids = [r[0] for r in record_ids_result.fetchall()]

    if record_ids:
        await session.execute(Personnel.__table__.delete().where(Personnel.record_id.in_(record_ids)))
        await session.execute(RecordCorrection.__table__.delete().where(RecordCorrection.record_id.in_(record_ids)))
        await session.execute(Record.__table__.delete().where(Record.id.in_(record_ids)))

    await session.execute(PipelineJob.__table__.delete().where(PipelineJob.collection_id == collection_id))
    await session.execute(Page.__table__.delete().where(Page.collection_id == collection_id))
    await session.delete(collection)
    await session.commit()

    return {"status": "deleted", "records_deleted": len(record_ids)}


@router.post("/{collection_id}/reset-extraction")
async def reset_extraction(
    collection_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete all extracted records for a collection so it can be re-extracted with a different model."""
    collection = await session.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Delete personnel (cascade from records), corrections, then records
    from app.db.models import Personnel, RecordCorrection
    records_result = await session.execute(
        select(Record.id)
        .join(Page, Record.page_id == Page.id)
        .where(Page.collection_id == collection_id)
    )
    record_ids = [r[0] for r in records_result.fetchall()]

    if record_ids:
        await session.execute(
            Personnel.__table__.delete().where(Personnel.record_id.in_(record_ids))
        )
        await session.execute(
            RecordCorrection.__table__.delete().where(RecordCorrection.record_id.in_(record_ids))
        )
        await session.execute(
            Record.__table__.delete().where(Record.id.in_(record_ids))
        )

    # Reset page statuses
    await session.execute(
        Page.__table__.update()
        .where(Page.collection_id == collection_id)
        .values(ocr_status="pending")
    )

    # Reset collection status
    collection.status = "pending"
    await session.commit()

    return {
        "status": "reset",
        "records_deleted": len(record_ids),
        "message": f"Cleared {len(record_ids)} records. Collection ready for re-extraction.",
    }


@router.post("/{collection_id}/extract")
async def start_extraction(
    collection_id: uuid.UUID,
    stage: str = "kraken",
    max_pages: int | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session),
):
    collection = await session.get(Collection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    result = await session.execute(
        select(func.count(Page.id)).where(Page.collection_id == collection_id)
    )
    page_count = result.scalar()
    effective_pages = min(page_count, max_pages) if max_pages else page_count

    job = PipelineJob(collection_id=collection_id, stage=stage, total_pages=effective_pages)
    session.add(job)
    await session.commit()
    await session.refresh(job)

    stage_map = {
        "kraken": run_kraken_stage_background,
        "claude": run_claude_stage_background,
        "embedding": run_embedding_stage_background,
    }
    bg_func = stage_map.get(stage)
    if not bg_func:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")

    background_tasks.add_task(bg_func, collection_id, job.id, max_pages)

    return {"job_id": str(job.id), "stage": stage, "status": "started", "max_pages": effective_pages}


@router.get("/{collection_id}/jobs")
async def list_jobs(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """List pipeline jobs for a collection, most recent first."""
    result = await session.execute(
        select(PipelineJob)
        .where(PipelineJob.collection_id == collection_id)
        .order_by(PipelineJob.started_at.desc().nulls_last())
    )
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "stage": j.stage,
            "status": j.status,
            "total_pages": j.total_pages,
            "processed_pages": j.processed_pages,
            "error_message": j.error_message,
        }
        for j in jobs
    ]


@router.get("/{collection_id}/pages")
async def list_pages(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Page).where(Page.collection_id == collection_id).order_by(Page.page_number)
    )
    pages = result.scalars().all()
    return [{"id": str(p.id), "page_number": p.page_number, "ocr_status": p.ocr_status} for p in pages]


@router.get("/{collection_id}/pages/{page_number}/records")
async def get_page_records(collection_id: uuid.UUID, page_number: int, session: AsyncSession = Depends(get_session)):
    page_result = await session.execute(
        select(Page).where(Page.collection_id == collection_id, Page.page_number == page_number)
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    records_result = await session.execute(
        select(Record)
        .where(Record.page_id == page.id)
        .options(selectinload(Record.personnel))
        .order_by(Record.entry_number)
    )
    records = records_result.scalars().all()

    return {
        "page": {"id": str(page.id), "image_path": page.image_path, "page_number": page.page_number},
        "records": [
            {
                "id": str(r.id),
                "entry_number": r.entry_number,
                "date": str(r.date) if r.date else None,
                "unit_designation": r.unit_designation,
                "aircraft_type": r.aircraft_type,
                "werknummer": r.werknummer,
                "incident_type": r.incident_type,
                "damage_percentage": r.damage_percentage,
                "personnel": [
                    {
                        "rank_abbreviation": p.rank_abbreviation,
                        "surname": p.surname,
                        "first_name": p.first_name,
                        "fate_english": p.fate_english,
                    }
                    for p in r.personnel
                ],
            }
            for r in records
        ],
    }


@router.get("/pages/image")
async def serve_image(path: str):
    image_path = Path(path).resolve()
    # Allow images from storage path or any path that exists (local dev)
    # TODO: In production, restrict to storage path only
    allowed_root = Path(settings.image_storage_path).resolve()
    if not str(image_path).startswith(str(allowed_root)) and not image_path.exists():
        raise HTTPException(status_code=403, detail="Access denied")
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)
