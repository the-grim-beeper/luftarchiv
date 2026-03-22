"""Tests for archive_knowledge schema models."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AircraftType, DocumentSchema, Glossary, UnitDesignation


@pytest.mark.asyncio
async def test_create_glossary_entry(db_session: AsyncSession):
    entry = Glossary(
        term="Abschuss",
        definition="Aerial victory / shoot-down of an enemy aircraft",
        category="combat_terminology",
        language="de",
        trust_level=2,
        source="Official Luftwaffe documentation",
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    assert entry.id is not None
    assert entry.term == "Abschuss"
    assert entry.trust_level == 2
    assert entry.verified_at is None


@pytest.mark.asyncio
async def test_create_unit_with_parent(db_session: AsyncSession):
    parent = UnitDesignation(
        abbreviation="JG 52",
        full_name="Jagdgeschwader 52",
        unit_type="Geschwader",
        trust_level=3,
    )
    db_session.add(parent)
    await db_session.flush()

    child = UnitDesignation(
        abbreviation="I./JG 52",
        full_name="I. Gruppe / Jagdgeschwader 52",
        unit_type="Gruppe",
        parent_unit_id=parent.id,
        trust_level=2,
    )
    db_session.add(child)
    await db_session.commit()
    await db_session.refresh(child)

    assert child.parent_unit_id == parent.id

    result = await db_session.execute(
        select(UnitDesignation).where(UnitDesignation.parent_unit_id == parent.id)
    )
    children = result.scalars().all()
    assert len(children) == 1
    assert children[0].abbreviation == "I./JG 52"


@pytest.mark.asyncio
async def test_create_aircraft_type(db_session: AsyncSession):
    aircraft = AircraftType(
        designation="Bf 109",
        manufacturer="Messerschmitt",
        common_name="Emil / Friedrich / Gustav",
        variants=["Bf 109 E", "Bf 109 F", "Bf 109 G", "Bf 109 K"],
        trust_level=3,
    )
    db_session.add(aircraft)
    await db_session.commit()
    await db_session.refresh(aircraft)

    assert aircraft.id is not None
    assert aircraft.designation == "Bf 109"
    assert "Bf 109 G" in aircraft.variants


@pytest.mark.asyncio
async def test_create_document_schema(db_session: AsyncSession):
    example_id = uuid.uuid4()
    schema = DocumentSchema(
        document_type="verlustliste",
        description="Luftwaffe aircraft loss list",
        column_definitions={
            "columns": [
                {"name": "entry_number", "type": "integer"},
                {"name": "date", "type": "date"},
                {"name": "unit", "type": "string"},
            ]
        },
        example_collection_id=example_id,
        trust_level=3,
    )
    db_session.add(schema)
    await db_session.commit()
    await db_session.refresh(schema)

    assert schema.id is not None
    assert schema.document_type == "verlustliste"
    assert schema.example_collection_id == example_id
    assert len(schema.column_definitions["columns"]) == 3


@pytest.mark.asyncio
async def test_document_schema_unique_document_type(db_session: AsyncSession):
    schema1 = DocumentSchema(document_type="unique_type", trust_level=1)
    schema2 = DocumentSchema(document_type="unique_type", trust_level=1)
    db_session.add(schema1)
    await db_session.flush()
    db_session.add(schema2)

    with pytest.raises(Exception):
        await db_session.flush()
