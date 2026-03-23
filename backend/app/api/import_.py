from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.collection import CollectionResponse
from app.services.import_service import import_scan_folder, SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/browse")
async def browse_folder(path: str = Query(default="")):
    """Browse server-side folders for the import dialog."""
    # Default: start at /scans (Docker mount) or home directory
    if not path:
        scans_dir = Path("/scans")
        path = str(scans_dir) if scans_dir.is_dir() else "~"
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not target.is_dir():
        target = target.parent

    # List subdirectories + count of image files
    entries = []
    try:
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                # Count images inside
                try:
                    image_count = sum(
                        1 for f in item.iterdir()
                        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
                    )
                except PermissionError:
                    image_count = 0
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory",
                    "image_count": image_count,
                })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return {
        "current": str(target),
        "parent": str(target.parent) if target != target.parent else None,
        "entries": entries,
    }


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
