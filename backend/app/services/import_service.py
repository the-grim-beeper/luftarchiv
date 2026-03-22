import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Collection, Page

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


async def import_scan_folder(
    session: AsyncSession,
    folder_path: Path,
    name: str,
    source_reference: str | None = None,
    description: str | None = None,
    document_type: str | None = None,
) -> Collection:
    """Import a folder of scanned images as a new collection."""
    image_files = sorted(
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    collection = Collection(
        name=name,
        source_reference=source_reference,
        description=description,
        document_type=document_type,
        page_count=len(image_files),
        status="pending",
    )
    session.add(collection)
    await session.flush()

    storage_dir = Path(settings.image_storage_path) / str(collection.id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    for i, image_file in enumerate(image_files, start=1):
        dest = storage_dir / image_file.name
        shutil.copy2(image_file, dest)

        page = Page(
            collection_id=collection.id,
            page_number=i,
            image_path=str(dest),
            ocr_status="pending",
        )
        session.add(page)

    await session.commit()
    await session.refresh(collection)
    return collection
