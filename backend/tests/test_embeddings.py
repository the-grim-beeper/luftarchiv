"""
Tests for the embedding service.
fastembed model download is mocked so tests run without network/disk access.
"""

import pytest
from unittest.mock import MagicMock, patch


# Override the autouse setup_db fixture — these tests don't need a database.
@pytest.fixture(autouse=True)
def setup_db():
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    date="1943-07-15",
    unit_designation="I./JG 52",
    aircraft_type="Bf 109 G",
    werknummer="160043",
    incident_type="Bruchlandung",
    incident_description="Forced landing due to engine failure.",
    damage_percentage="80",
    location="Kursk",
    raw_text_original=None,
    personnel=None,
):
    """Return a lightweight object mimicking a Record model instance."""
    rec = MagicMock()
    rec.date = date
    rec.unit_designation = unit_designation
    rec.aircraft_type = aircraft_type
    rec.werknummer = werknummer
    rec.incident_type = incident_type
    rec.incident_description = incident_description
    rec.damage_percentage = damage_percentage
    rec.location = location
    rec.raw_text_original = raw_text_original
    rec.personnel = personnel or []
    return rec


def _make_person(rank_abbreviation="Uffz.", surname="Müller", first_name="Hans", fate="verwundet"):
    p = MagicMock()
    p.rank_abbreviation = rank_abbreviation
    p.rank_full = "Unteroffizier"
    p.surname = surname
    p.first_name = first_name
    p.fate = fate
    p.fate_english = "wounded"
    return p


# ---------------------------------------------------------------------------
# generate_record_summary tests
# ---------------------------------------------------------------------------

def test_summary_contains_key_fields():
    from app.services.embeddings import generate_record_summary

    record = _make_record()
    summary = generate_record_summary(record)

    assert "1943-07-15" in summary
    assert "I./JG 52" in summary
    assert "Bf 109 G" in summary
    assert "Bruchlandung" in summary
    assert "Kursk" in summary
    assert "80" in summary


def test_summary_includes_personnel():
    from app.services.embeddings import generate_record_summary

    person = _make_person()
    record = _make_record(personnel=[person])
    summary = generate_record_summary(record)

    assert "Müller" in summary
    assert "Uffz." in summary
    assert "verwundet" in summary


def test_summary_empty_record():
    from app.services.embeddings import generate_record_summary

    rec = MagicMock()
    rec.date = None
    rec.unit_designation = None
    rec.aircraft_type = None
    rec.werknummer = None
    rec.incident_type = None
    rec.incident_description = None
    rec.damage_percentage = None
    rec.location = None
    rec.raw_text_original = None
    rec.personnel = []

    summary = generate_record_summary(rec)
    assert summary == "No data."


def test_summary_raw_text_truncation():
    from app.services.embeddings import generate_record_summary

    long_text = "X" * 1000
    record = _make_record(raw_text_original=long_text)
    summary = generate_record_summary(record)

    # Raw text should be truncated to 500 chars — no more than 500 X's
    assert summary.count("X") <= 500


# ---------------------------------------------------------------------------
# generate_embedding tests  (mocked fastembed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_embedding_returns_correct_dims():
    import numpy as np

    fake_vector = np.zeros(1024, dtype="float32")
    mock_model = MagicMock()
    mock_model.embed.return_value = iter([fake_vector])

    with patch("app.services.embeddings._get_model", return_value=mock_model):
        from app.services.embeddings import generate_embedding

        result = await generate_embedding("test query")

    assert isinstance(result, list)
    assert len(result) == 1024
    assert all(isinstance(v, float) for v in result)


@pytest.mark.asyncio
async def test_generate_embedding_passes_text_to_model():
    import numpy as np

    fake_vector = np.ones(1024, dtype="float32")
    mock_model = MagicMock()
    mock_model.embed.return_value = iter([fake_vector])

    with patch("app.services.embeddings._get_model", return_value=mock_model):
        from app.services.embeddings import generate_embedding

        result = await generate_embedding("Bruchlandung Bf 109")

    mock_model.embed.assert_called_once_with(["Bruchlandung Bf 109"])
    assert len(result) == 1024
