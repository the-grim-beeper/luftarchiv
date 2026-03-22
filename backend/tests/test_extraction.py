"""Tests for the extraction pipeline orchestrator.

These tests require a running PostgreSQL test instance (port 5435).
If the DB is not available they will be skipped gracefully.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import Collection, Page, PipelineJob
from app.services.extraction import run_kraken_stage


@pytest.mark.asyncio
@patch("app.services.ocr_kraken.kraken_ocr_page", new_callable=AsyncMock)
async def test_run_kraken_stage(mock_kraken, db_session):
    mock_kraken.return_value = {
        "raw_text": "Test OCR output",
        "segmentation": [{"text": "Test OCR output", "bbox": {"x": 0, "y": 0, "w": 100, "h": 30}}],
    }

    collection = Collection(name="Test", status="pending", page_count=1)
    db_session.add(collection)
    await db_session.commit()

    page = Page(
        collection_id=collection.id,
        page_number=1,
        image_path="/test.jpg",
        ocr_status="pending",
    )
    db_session.add(page)
    await db_session.commit()

    job = PipelineJob(collection_id=collection.id, stage="kraken", total_pages=1)
    db_session.add(job)
    await db_session.commit()

    with patch("app.services.extraction.kraken_ocr_page", mock_kraken):
        await run_kraken_stage(db_session, collection.id, job.id)

    await db_session.refresh(page)
    assert page.raw_ocr_text == "Test OCR output"
    assert page.ocr_status == "extracted"
    assert page.segmentation_data is not None

    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.processed_pages == 1


@pytest.mark.asyncio
@patch("app.services.ocr_kraken.kraken_ocr_page", new_callable=AsyncMock)
async def test_run_kraken_stage_failure(mock_kraken, db_session):
    """When Kraken raises an exception the job is marked as failed."""
    mock_kraken.side_effect = RuntimeError("OCR engine error")

    collection = Collection(name="Fail Test", status="pending", page_count=1)
    db_session.add(collection)
    await db_session.commit()

    page = Page(
        collection_id=collection.id,
        page_number=1,
        image_path="/nonexistent.jpg",
        ocr_status="pending",
    )
    db_session.add(page)
    await db_session.commit()

    job = PipelineJob(collection_id=collection.id, stage="kraken", total_pages=1)
    db_session.add(job)
    await db_session.commit()

    with patch("app.services.extraction.kraken_ocr_page", mock_kraken):
        await run_kraken_stage(db_session, collection.id, job.id)

    await db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_message is not None
    assert "page 1" in job.error_message


@pytest.mark.asyncio
async def test_run_kraken_stage_no_pending_pages(db_session):
    """A collection with no pending pages completes immediately with 0 processed."""
    collection = Collection(name="Empty Test", status="pending", page_count=0)
    db_session.add(collection)
    await db_session.commit()

    job = PipelineJob(collection_id=collection.id, stage="kraken", total_pages=0)
    db_session.add(job)
    await db_session.commit()

    await run_kraken_stage(db_session, collection.id, job.id)

    await db_session.refresh(job)
    assert job.status == "completed"
    assert job.processed_pages == 0
