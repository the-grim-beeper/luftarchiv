"""Tests for the Knowledge CRUD API (glossary, units, aircraft)."""

import pytest


async def test_create_and_list_glossary(client):
    # Create an entry
    resp = await client.post(
        "/api/knowledge/glossary",
        json={
            "term": "Bruchlandung",
            "definition": "Crash landing",
            "category": "incident_type",
            "trust_level": 0,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["term"] == "Bruchlandung"
    assert data["category"] == "incident_type"
    entry_id = data["id"]

    # List all
    resp = await client.get("/api/knowledge/glossary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    terms = [item["term"] for item in body["items"]]
    assert "Bruchlandung" in terms

    # Filter by category
    resp = await client.get("/api/knowledge/glossary?category=incident_type")
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["category"] == "incident_type" for item in body["items"])

    # Filter by trust_level
    resp = await client.get("/api/knowledge/glossary?trust_level=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


async def test_review_glossary_approve(client):
    # Create
    resp = await client.post(
        "/api/knowledge/glossary",
        json={"term": "Notlandung", "definition": "Emergency landing", "category": "incident_type"},
    )
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # Approve
    resp = await client.post(
        f"/api/knowledge/glossary/{entry_id}/review",
        json={"action": "approve", "reason": "Verified from primary source"},
    )
    assert resp.status_code == 200, resp.text
    review = resp.json()
    assert review["action"] == "approve"
    assert review["new_trust_level"] == 2
    assert review["old_trust_level"] == 0

    # Confirm trust_level was updated on the entry
    resp = await client.get("/api/knowledge/glossary?trust_level=2")
    assert resp.status_code == 200
    terms = [item["term"] for item in resp.json()["items"]]
    assert "Notlandung" in terms


async def test_review_glossary_reject(client):
    resp = await client.post(
        "/api/knowledge/glossary",
        json={"term": "Spamentry", "definition": "Bogus", "category": "other"},
    )
    entry_id = resp.json()["id"]

    resp = await client.post(
        f"/api/knowledge/glossary/{entry_id}/review",
        json={"action": "reject", "reason": "Inaccurate"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_trust_level"] == -1


async def test_review_glossary_invalid_action(client):
    resp = await client.post(
        "/api/knowledge/glossary",
        json={"term": "TestEntry", "definition": "test"},
    )
    entry_id = resp.json()["id"]

    resp = await client.post(
        f"/api/knowledge/glossary/{entry_id}/review",
        json={"action": "invalid_action"},
    )
    assert resp.status_code == 400


async def test_review_glossary_not_found(client):
    import uuid

    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/knowledge/glossary/{fake_id}/review",
        json={"action": "approve"},
    )
    assert resp.status_code == 404


async def test_create_and_list_units(client):
    resp = await client.post(
        "/api/knowledge/units",
        json={
            "abbreviation": "JG 52",
            "full_name": "Jagdgeschwader 52",
            "unit_type": "Geschwader",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["abbreviation"] == "JG 52"

    resp = await client.get("/api/knowledge/units")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    abbrevs = [u["abbreviation"] for u in body["items"]]
    assert "JG 52" in abbrevs


async def test_create_and_list_aircraft(client):
    resp = await client.post(
        "/api/knowledge/aircraft",
        json={
            "designation": "Bf 109",
            "manufacturer": "Messerschmitt",
            "common_name": "Emil",
            "variants": ["Bf 109 E", "Bf 109 F", "Bf 109 G"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["designation"] == "Bf 109"
    assert "Bf 109 G" in data["variants"]

    resp = await client.get("/api/knowledge/aircraft")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    designations = [a["designation"] for a in body["items"]]
    assert "Bf 109" in designations
