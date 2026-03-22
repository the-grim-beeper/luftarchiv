"""Tests for the Claude extraction service (Stage 2 of the OCR pipeline).

All tests mock ``_call_claude`` so they pass without a real Anthropic API key
or network access.

These tests do not require a database connection.  The ``setup_db`` autouse
fixture defined in conftest.py would otherwise attempt to connect to the test
PostgreSQL instance.  We override it here with a no-op so the Claude tests can
run in isolation without any database infrastructure.
"""

from unittest.mock import patch

import pytest

from app.services.ocr_claude import extract_records_from_page, build_extraction_prompt


# ---------------------------------------------------------------------------
# Override the autouse DB fixture so these tests don't need Postgres running
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def setup_db():  # noqa: F811 — intentional override of conftest fixture
    """No-op override: Claude extraction tests need no database."""
    yield


# ---------------------------------------------------------------------------
# Fixtures / shared data
# ---------------------------------------------------------------------------

MOCK_RESPONSE = {
    "records": [
        {
            "entry_number": 1,
            "date": "1943-03-15",
            "unit_designation": "II./JG 54",
            "aircraft_type": "Bf 109 G-4",
            "werknummer": "19241",
            "incident_type": "Bruchlandung",
            "incident_description": "Crash landing due to engine failure",
            "damage_percentage": 40,
            "location": "Krasnogvardeisk",
            "personnel": [
                {
                    "rank_abbreviation": "Uffz.",
                    "rank_full": "Unteroffizier",
                    "surname": "Schmidt",
                    "first_name": "Werner",
                    "fate": "unverletzt",
                    "fate_english": "uninjured",
                }
            ],
            "new_abbreviations": [],
        }
    ]
}


# ---------------------------------------------------------------------------
# build_extraction_prompt tests
# ---------------------------------------------------------------------------


def test_build_extraction_prompt():
    """Prompt contains OCR text, glossary terms, and JSON keyword."""
    prompt = build_extraction_prompt(
        raw_ocr_text="1. 15.3.43 II./JG 54 Bf 109 G-4 Bruchlandung 40%",
        glossary_context={"Bruchlandung": "crash landing", "Uffz.": "Unteroffizier"},
    )
    assert "Bruchlandung" in prompt
    assert "crash landing" in prompt
    assert "JSON" in prompt or "json" in prompt


def test_build_extraction_prompt_empty_glossary():
    """Prompt degrades gracefully when no glossary entries are supplied."""
    prompt = build_extraction_prompt(
        raw_ocr_text="15.3.43 JG 51",
        glossary_context={},
    )
    assert "15.3.43" in prompt
    assert "No glossary entries provided" in prompt


def test_build_extraction_prompt_includes_ocr_text():
    """All raw OCR text appears verbatim in the prompt."""
    ocr = "Some unique OCR content 12345"
    prompt = build_extraction_prompt(raw_ocr_text=ocr, glossary_context={})
    assert ocr in prompt


# ---------------------------------------------------------------------------
# extract_records_from_page tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.ocr_claude._call_claude")
async def test_extract_records(mock_call):
    """Returns the records list from Claude's structured response."""
    mock_call.return_value = MOCK_RESPONSE

    records = await extract_records_from_page(
        image_path="/test/image.jpg",
        raw_ocr_text="1. 15.3.43 II./JG 54",
        glossary_context={},
    )

    assert len(records) == 1
    assert records[0]["unit_designation"] == "II./JG 54"
    assert records[0]["personnel"][0]["surname"] == "Schmidt"
    assert records[0]["date"] == "1943-03-15"


@pytest.mark.asyncio
@patch("app.services.ocr_claude._call_claude")
async def test_extract_records_returns_empty_list_when_no_records(mock_call):
    """Returns an empty list when Claude finds no records on the page."""
    mock_call.return_value = {"records": []}

    records = await extract_records_from_page(
        image_path="/test/blank.jpg",
        raw_ocr_text="",
        glossary_context={},
    )

    assert records == []


@pytest.mark.asyncio
@patch("app.services.ocr_claude._call_claude")
async def test_extract_records_missing_records_key(mock_call):
    """Gracefully handles a response dict that lacks a 'records' key."""
    mock_call.return_value = {}

    records = await extract_records_from_page(
        image_path="/test/image.jpg",
        raw_ocr_text="some text",
        glossary_context={},
    )

    assert records == []


@pytest.mark.asyncio
@patch("app.services.ocr_claude._call_claude")
async def test_extract_records_passes_glossary_to_prompt(mock_call):
    """Glossary context is forwarded correctly to the underlying API call."""
    mock_call.return_value = MOCK_RESPONSE

    glossary = {"Bruchlandung": "crash landing"}
    await extract_records_from_page(
        image_path="/test/image.jpg",
        raw_ocr_text="some ocr text",
        glossary_context=glossary,
    )

    # _call_claude should have been called once; inspect the prompt argument
    assert mock_call.call_count == 1
    _, prompt_arg = mock_call.call_args[0]
    assert "Bruchlandung" in prompt_arg
    assert "crash landing" in prompt_arg


@pytest.mark.asyncio
@patch("app.services.ocr_claude._call_claude")
async def test_extract_records_personnel_fields(mock_call):
    """Personnel sub-records are returned with all expected fields."""
    mock_call.return_value = MOCK_RESPONSE

    records = await extract_records_from_page(
        image_path="/test/image.jpg",
        raw_ocr_text="1. 15.3.43 II./JG 54",
        glossary_context={},
    )

    person = records[0]["personnel"][0]
    assert person["rank_abbreviation"] == "Uffz."
    assert person["rank_full"] == "Unteroffizier"
    assert person["fate"] == "unverletzt"
    assert person["fate_english"] == "uninjured"
