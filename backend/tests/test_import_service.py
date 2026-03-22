import tempfile
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.db.models import Collection, Page
from app.services.import_service import import_scan_folder


def create_test_images(folder: Path, count: int = 3):
    for i in range(1, count + 1):
        img = Image.new("RGB", (100, 100), color="white")
        img.save(folder / f"test_{i:04d}.jpg")


async def test_import_scan_folder(db_session):
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        create_test_images(folder, count=3)

        collection = await import_scan_folder(
            session=db_session,
            folder_path=folder,
            name="Test Collection",
            source_reference="TEST_001",
        )

        assert collection.name == "Test Collection"
        assert collection.page_count == 3
        assert collection.status == "pending"

        # Query pages explicitly (not lazy load in async)
        result = await db_session.execute(
            select(Page).where(Page.collection_id == collection.id).order_by(Page.page_number)
        )
        pages = result.scalars().all()
        assert len(pages) == 3
        assert pages[0].page_number == 1
        assert pages[2].page_number == 3
        assert pages[0].ocr_status == "pending"


async def test_import_skips_non_images(db_session):
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        create_test_images(folder, count=1)
        (folder / "readme.txt").write_text("not an image")

        collection = await import_scan_folder(
            session=db_session,
            folder_path=folder,
            name="Mixed files",
        )
        assert collection.page_count == 1
