"""Tests for the Kraken OCR service wrapper.

All tests mock ``_run_kraken`` so they pass regardless of whether Kraken is
installed in the environment.

These tests do not require a database connection.  The ``setup_db`` autouse
fixture defined in conftest.py would otherwise attempt to connect to the test
PostgreSQL instance.  We override it here with a no-op so the OCR tests can
run in isolation without any database infrastructure.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.services.ocr_kraken import kraken_ocr_page


# ---------------------------------------------------------------------------
# Override the autouse DB fixture so these tests don't need Postgres running
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def setup_db():  # noqa: F811 — intentional override of conftest fixture
    """No-op override: OCR tests need no database."""
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_test_image(path: Path) -> None:
    """Create a minimal white JPEG image for use as OCR input."""
    img = Image.new("RGB", (800, 200), color="white")
    img.save(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kraken_ocr_returns_expected_structure():
    """Service returns the expected dict structure with correct types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.jpg"
        create_test_image(img_path)

        mock_result = {
            "raw_text": "Test line one\nTest line two",
            "segmentation": [
                {"text": "Test line one", "bbox": {"x": 10, "y": 20, "w": 200, "h": 30}},
                {"text": "Test line two", "bbox": {"x": 10, "y": 60, "w": 180, "h": 30}},
            ],
        }

        with patch("app.services.ocr_kraken._run_kraken", return_value=mock_result):
            result = await kraken_ocr_page(img_path)

        assert "raw_text" in result
        assert "segmentation" in result
        assert isinstance(result["raw_text"], str)
        assert isinstance(result["segmentation"], list)
        assert len(result["segmentation"]) == 2
        assert result["segmentation"][0]["text"] == "Test line one"
        assert "bbox" in result["segmentation"][0]


@pytest.mark.asyncio
async def test_kraken_ocr_bbox_fields():
    """Each segmentation entry has all required bbox fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.jpg"
        create_test_image(img_path)

        mock_result = {
            "raw_text": "Hello world",
            "segmentation": [
                {"text": "Hello world", "bbox": {"x": 5, "y": 10, "w": 150, "h": 30}},
            ],
        }

        with patch("app.services.ocr_kraken._run_kraken", return_value=mock_result):
            result = await kraken_ocr_page(img_path)

        bbox = result["segmentation"][0]["bbox"]
        for key in ("x", "y", "w", "h"):
            assert key in bbox, f"bbox is missing key '{key}'"


@pytest.mark.asyncio
async def test_kraken_graceful_without_kraken():
    """Service returns empty but valid result when Kraken is not installed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.jpg"
        create_test_image(img_path)

        mock_result = {"raw_text": "", "segmentation": []}

        with patch("app.services.ocr_kraken._run_kraken", return_value=mock_result):
            result = await kraken_ocr_page(img_path)

        assert result["raw_text"] == ""
        assert result["segmentation"] == []


@pytest.mark.asyncio
async def test_kraken_accepts_string_path():
    """Service accepts a plain string as the image_path argument."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test.jpg"
        create_test_image(img_path)

        mock_result = {"raw_text": "Some text", "segmentation": []}

        with patch("app.services.ocr_kraken._run_kraken", return_value=mock_result) as mock:
            result = await kraken_ocr_page(str(img_path))  # pass a str, not a Path

        # Verify _run_kraken was called with a Path object (coerced internally)
        called_arg = mock.call_args[0][0]
        assert isinstance(called_arg, Path)
        assert result["raw_text"] == "Some text"


@pytest.mark.asyncio
async def test_kraken_empty_page():
    """Service handles an image that produces no recognised lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "blank.jpg"
        create_test_image(img_path)

        mock_result = {"raw_text": "", "segmentation": []}

        with patch("app.services.ocr_kraken._run_kraken", return_value=mock_result):
            result = await kraken_ocr_page(img_path)

        assert result["raw_text"] == ""
        assert result["segmentation"] == []
