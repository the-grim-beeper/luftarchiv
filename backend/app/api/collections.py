import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Collection, Page, PipelineJob
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


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    await session.delete(collection)
    await session.commit()


@router.post("/{collection_id}/extract")
async def start_extraction(
    collection_id: uuid.UUID,
    stage: str = "kraken",
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

    job = PipelineJob(collection_id=collection_id, stage=stage, total_pages=page_count)
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

    background_tasks.add_task(bg_func, collection_id, job.id)

    return {"job_id": str(job.id), "stage": stage, "status": "started"}
