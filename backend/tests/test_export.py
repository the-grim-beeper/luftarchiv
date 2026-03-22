"""
Tests for the export service and API endpoint.
"""

import csv
import io
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Page, Personnel, Record
from app.services.export import export_records_to_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_collection(session: AsyncSession, name: str = "Export Test") -> Collection:
    collection = Collection(name=name)
    session.add(collection)
    await session.flush()

    page = Page(collection_id=collection.id, page_number=1)
    session.add(page)
    await session.flush()

    record = Record(
        page_id=page.id,
        date="1943-07-15",
        unit_designation="I./JG 52",
        aircraft_type="Bf 109 G",
        incident_type="Bruchlandung",
        location="Kursk",
        entry_number=1,
    )
    session.add(record)
    await session.flush()

    p1 = Personnel(
        record_id=record.id,
        rank_abbreviation="Uffz.",
        surname="Müller",
        first_name="Hans",
        fate="verwundet",
        fate_english="wounded",
    )
    p2 = Personnel(
        record_id=record.id,
        rank_abbreviation="Oblt.",
        surname="Schmidt",
        first_name="Kurt",
        fate="unverletzt",
        fate_english="uninjured",
    )
    session.add_all([p1, p2])
    await session.commit()
    return collection


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

async def test_export_returns_csv_string(db_session: AsyncSession):
    collection = await _seed_collection(db_session)
    csv_str, filename = await export_records_to_csv(collection.id, db_session)

    assert isinstance(csv_str, str)
    assert len(csv_str) > 0
    assert filename.endswith(".csv")
    assert str(collection.id) in filename


async def test_export_csv_has_expected_headers(db_session: AsyncSession):
    collection = await _seed_collection(db_session)
    csv_str, _ = await export_records_to_csv(collection.id, db_session)

    reader = csv.DictReader(io.StringIO(csv_str))
    headers = reader.fieldnames or []

    assert "date" in headers
    assert "unit_designation" in headers
    assert "aircraft_type" in headers
    assert "incident_type" in headers
    assert "location" in headers
    # Personnel columns should exist for 2 people
    assert "person_1_surname" in headers
    assert "person_2_surname" in headers


async def test_export_csv_row_data(db_session: AsyncSession):
    collection = await _seed_collection(db_session)
    csv_str, _ = await export_records_to_csv(collection.id, db_session)

    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 1

    row = rows[0]
    assert row["date"] == "1943-07-15"
    assert row["unit_designation"] == "I./JG 52"
    assert row["aircraft_type"] == "Bf 109 G"
    assert row["incident_type"] == "Bruchlandung"

    # Personnel — order depends on insertion order
    surnames = {row["person_1_surname"], row["person_2_surname"]}
    assert "Müller" in surnames
    assert "Schmidt" in surnames


async def test_export_collection_not_found_raises(db_session: AsyncSession):
    with pytest.raises(ValueError, match="not found"):
        await export_records_to_csv(uuid.uuid4(), db_session)


async def test_export_empty_collection(db_session: AsyncSession):
    collection = Collection(name="Empty Collection")
    db_session.add(collection)
    await db_session.commit()

    csv_str, filename = await export_records_to_csv(collection.id, db_session)
    lines = csv_str.strip().splitlines()
    # Only header row
    assert len(lines) == 1


# ---------------------------------------------------------------------------
# API endpoint test
# ---------------------------------------------------------------------------

async def test_export_api_endpoint(client, db_session: AsyncSession):
    collection = await _seed_collection(db_session, name="API Export Test")

    resp = await client.get(f"/api/export/{collection.id}/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.text.strip() != ""


async def test_export_api_not_found(client):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/export/{fake_id}/csv")
    assert resp.status_code == 404
