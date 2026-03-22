import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Collection
from app.schemas.collection import CollectionCreate, CollectionList, CollectionResponse

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
