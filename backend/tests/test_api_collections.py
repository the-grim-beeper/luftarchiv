async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_create_and_list_collections(client):
    resp = await client.post("/api/collections", json={
        "name": "RL 2-III/1190",
        "source_reference": "RL_2_III_1190",
        "description": "Luftwaffe loss reports",
        "document_type": "loss_report",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "RL 2-III/1190"
    assert data["status"] == "pending"
    collection_id = data["id"]

    resp = await client.get("/api/collections")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = await client.get(f"/api/collections/{collection_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "RL 2-III/1190"


async def test_delete_collection(client):
    resp = await client.post("/api/collections", json={"name": "To delete"})
    collection_id = resp.json()["id"]

    resp = await client.delete(f"/api/collections/{collection_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/collections/{collection_id}")
    assert resp.status_code == 404
