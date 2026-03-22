"""
Tests for the search service — direct search filters.
These tests require the database, so they use the autouse setup_db fixture.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Collection, Page, Personnel, Record
from app.schemas.search import SearchFilters
from app.services.search import direct_search


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

async def _create_test_record(
    session: AsyncSession,
    *,
    date: str = "1943-07-15",
    unit_designation: str = "I./JG 52",
    aircraft_type: str = "Bf 109 G",
    incident_type: str = "Bruchlandung",
    location: str = "Kursk",
    incident_description: str = "Engine failure forced landing",
    personnel: list[dict] | None = None,
) -> Record:
    collection = Collection(name="Test Collection")
    session.add(collection)
    await session.flush()

    page = Page(collection_id=collection.id, page_number=1)
    session.add(page)
    await session.flush()

    record = Record(
        page_id=page.id,
        date=date,
        unit_designation=unit_designation,
        aircraft_type=aircraft_type,
        incident_type=incident_type,
        location=location,
        incident_description=incident_description,
    )
    session.add(record)
    await session.flush()

    for p in (personnel or []):
        person = Personnel(record_id=record.id, **p)
        session.add(person)

    await session.commit()
    await session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_direct_search_no_filters(db_session: AsyncSession):
    await _create_test_record(db_session)
    filters = SearchFilters()
    results = await direct_search(filters, db_session)
    assert len(results) >= 1


async def test_direct_search_by_unit(db_session: AsyncSession):
    await _create_test_record(db_session, unit_designation="III./JG 3")
    await _create_test_record(db_session, unit_designation="KG 51")

    filters = SearchFilters(unit="JG 3")
    results = await direct_search(filters, db_session)
    assert all("JG 3" in (r.unit_designation or "") for r in results)
    units = [r.unit_designation for r in results]
    assert "III./JG 3" in units
    assert "KG 51" not in units


async def test_direct_search_by_aircraft_type(db_session: AsyncSession):
    await _create_test_record(db_session, aircraft_type="Fw 190 A")
    await _create_test_record(db_session, aircraft_type="Ju 88")

    filters = SearchFilters(aircraft_type="Fw 190")
    results = await direct_search(filters, db_session)
    types = [r.aircraft_type for r in results]
    assert "Fw 190 A" in types
    assert "Ju 88" not in types


async def test_direct_search_by_incident_type(db_session: AsyncSession):
    await _create_test_record(db_session, incident_type="Bruchlandung")
    await _create_test_record(db_session, incident_type="Luftkampf")

    filters = SearchFilters(incident_type="Luftkampf")
    results = await direct_search(filters, db_session)
    types = [r.incident_type for r in results]
    assert "Luftkampf" in types
    assert "Bruchlandung" not in types


async def test_direct_search_by_free_text(db_session: AsyncSession):
    await _create_test_record(
        db_session, incident_description="Aircraft destroyed by flak over Berlin"
    )
    await _create_test_record(
        db_session, incident_description="Engine failure over Kursk"
    )

    filters = SearchFilters(free_text="flak")
    results = await direct_search(filters, db_session)
    descriptions = [r.incident_description for r in results]
    assert any("flak" in (d or "").lower() for d in descriptions)
    assert not any("Engine failure" in (d or "") for d in descriptions)


async def test_direct_search_by_personnel_name(db_session: AsyncSession):
    await _create_test_record(
        db_session,
        personnel=[{"surname": "Hartmann", "first_name": "Erich", "rank_abbreviation": "Oblt."}],
    )
    await _create_test_record(
        db_session,
        personnel=[{"surname": "Barkhorn", "first_name": "Gerhard", "rank_abbreviation": "Oblt."}],
    )

    filters = SearchFilters(personnel_name="Hartmann")
    results = await direct_search(filters, db_session)
    assert len(results) >= 1
    for record in results:
        surnames = [p.surname for p in record.personnel]
        assert "Hartmann" in surnames


async def test_direct_search_date_range(db_session: AsyncSession):
    await _create_test_record(db_session, date="1943-01-01")
    await _create_test_record(db_session, date="1944-06-06")
    await _create_test_record(db_session, date="1945-05-08")

    filters = SearchFilters(date_from="1944-01-01", date_to="1944-12-31")
    results = await direct_search(filters, db_session)
    dates = [r.date for r in results]
    assert "1944-06-06" in dates
    assert "1943-01-01" not in dates
    assert "1945-05-08" not in dates


async def test_direct_search_pagination(db_session: AsyncSession):
    for i in range(5):
        await _create_test_record(db_session, unit_designation="JG 99", date=f"1943-0{i+1}-01")

    filters = SearchFilters(unit="JG 99", limit=2, offset=0)
    page1 = await direct_search(filters, db_session)
    assert len(page1) == 2

    filters2 = SearchFilters(unit="JG 99", limit=2, offset=2)
    page2 = await direct_search(filters2, db_session)
    assert len(page2) == 2

    # IDs should not overlap
    ids1 = {r.id for r in page1}
    ids2 = {r.id for r in page2}
    assert ids1.isdisjoint(ids2)


async def test_direct_search_personnel_eagerly_loaded(db_session: AsyncSession):
    """Personnel relationship must be loaded without lazy-load errors."""
    await _create_test_record(
        db_session,
        personnel=[
            {"surname": "Rall", "rank_abbreviation": "Maj."},
            {"surname": "Nowotny", "rank_abbreviation": "Maj."},
        ],
    )

    filters = SearchFilters()
    results = await direct_search(filters, db_session)
    assert len(results) >= 1
    # Access personnel without raising DetachedInstanceError
    for r in results:
        _ = [p.surname for p in r.personnel]
