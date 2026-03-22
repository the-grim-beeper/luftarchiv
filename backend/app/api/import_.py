from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.collection import CollectionResponse
from app.services.import_service import import_scan_folder

router = APIRouter(prefix="/api/import", tags=["import"])


class ImportRequest(BaseModel):
    folder_path: str
    name: str
    source_reference: str | None = None
    description: str | None = None
    document_type: str | None = None


@router.post("", response_model=CollectionResponse, status_code=201)
async def import_folder(data: ImportRequest, session: AsyncSession = Depends(get_session)):
    folder = Path(data.folder_path)
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder not found: {data.folder_path}")

    collection = await import_scan_folder(
        session=session,
        folder_path=folder,
        name=data.name,
        source_reference=data.source_reference,
        description=data.description,
        document_type=data.document_type,
    )
    return collection
