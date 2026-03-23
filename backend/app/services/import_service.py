import shutil
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import Collection, Page

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

BATCH_SIZE = 20  # Commit pages in batches to avoid long transactions


async def import_scan_folder(
    session: AsyncSession,
    folder_path: Path,
    name: str,
    source_reference: str | None = None,
    description: str | None = None,
    document_type: str | None = None,
) -> Collection:
    """Create the collection record and count images. Does NOT copy files.

    Returns the collection immediately so the API can respond fast.
    File copying happens in import_scan_folder_background().
    """
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
        status="importing",
    )
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


async def import_scan_folder_background(
    collection_id: uuid.UUID,
    folder_path: Path,
) -> None:
    """Copy images and create page records in batches. Runs in background."""
    image_files = sorted(
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    storage_dir = Path(settings.image_storage_path) / str(collection_id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    async with SessionLocal() as session:
        batch: list[Page] = []

        for i, image_file in enumerate(image_files, start=1):
            dest = storage_dir / image_file.name
            shutil.copy2(image_file, dest)

            page = Page(
                collection_id=collection_id,
                page_number=i,
                image_path=str(dest),
                ocr_status="pending",
            )
            batch.append(page)

            # Commit in batches
            if len(batch) >= BATCH_SIZE:
                session.add_all(batch)
                await session.commit()
                batch.clear()

        # Commit remaining
        if batch:
            session.add_all(batch)
            await session.commit()

        # Mark collection as ready
        collection = await session.get(Collection, collection_id)
        if collection:
            collection.status = "pending"  # Ready for extraction
            await session.commit()
