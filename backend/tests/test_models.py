"""Tests for archive_data schema models."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Page, Personnel, Record, User


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user = User(username="testuser", role="editor")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == "testuser"
    assert user.role == "editor"
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_create_collection(db_session: AsyncSession):
    collection = Collection(
        name="Test Collection",
        source_reference="NARA-T971-001",
        description="A test collection of Luftwaffe records",
        document_type="verlustliste",
        page_count=50,
        status="pending",
    )
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)

    assert collection.id is not None
    assert collection.name == "Test Collection"
    assert collection.status == "pending"
    assert collection.created_at is not None


@pytest.mark.asyncio
async def test_collection_with_pages(db_session: AsyncSession):
    collection = Collection(
        name="Collection With Pages",
        status="processing",
    )
    db_session.add(collection)
    await db_session.flush()

    page1 = Page(
        collection_id=collection.id,
        page_number=1,
        image_path="/data/images/page1.jpg",
        ocr_status="completed",
        ocr_confidence=0.95,
        raw_ocr_text="Sample OCR text from page 1",
        segmentation_data={"rows": [{"y": 100, "height": 20}]},
    )
    page2 = Page(
        collection_id=collection.id,
        page_number=2,
        image_path="/data/images/page2.jpg",
        ocr_status="pending",
    )
    db_session.add_all([page1, page2])
    await db_session.commit()

    result = await db_session.execute(
        select(Page).where(Page.collection_id == collection.id)
    )
    pages = result.scalars().all()

    assert len(pages) == 2
    page_numbers = {p.page_number for p in pages}
    assert page_numbers == {1, 2}


@pytest.mark.asyncio
async def test_record_with_personnel(db_session: AsyncSession):
    collection = Collection(name="Records Collection", status="completed")
    db_session.add(collection)
    await db_session.flush()

    page = Page(
        collection_id=collection.id,
        page_number=1,
        ocr_status="completed",
    )
    db_session.add(page)
    await db_session.flush()

    record = Record(
        page_id=page.id,
        entry_number=42,
        date="1944-06-15",
        unit_designation="JG 52",
        aircraft_type="Bf 109 G-6",
        werknummer="163456",
        incident_type="Abschuss",
        incident_description="Abgeschossen durch feindliches Flugzeug",
        damage_percentage="100%",
        location="Ostfront",
        raw_text_original="42  15.6.44  JG52  Bf109G-6  163456  Abschuss  ...",
        bounding_boxes={"row": {"x": 0, "y": 100, "w": 800, "h": 20}},
    )
    db_session.add(record)
    await db_session.flush()

    person = Personnel(
        record_id=record.id,
        rank_abbreviation="Uffz.",
        rank_full="Unteroffizier",
        surname="Müller",
        first_name="Hans",
        fate="gefallen",
        fate_english="killed in action",
    )
    db_session.add(person)
    await db_session.commit()

    result = await db_session.execute(
        select(Personnel).where(Personnel.record_id == record.id)
    )
    personnel = result.scalars().all()

    assert len(personnel) == 1
    p = personnel[0]
    assert p.surname == "Müller"
    assert p.rank_abbreviation == "Uffz."
    assert p.fate_english == "killed in action"


@pytest.mark.asyncio
async def test_record_uses_page_foreign_key(db_session: AsyncSession):
    """Verify record.page relationship resolves via page_id FK."""
    collection = Collection(name="FK Test Collection", status="pending")
    db_session.add(collection)
    await db_session.flush()

    page = Page(collection_id=collection.id, page_number=1, ocr_status="pending")
    db_session.add(page)
    await db_session.flush()

    record = Record(page_id=page.id, entry_number=1)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.page_id == page.id
    assert record.page_id_end is None
