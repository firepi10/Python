def test_countdown_crud(client):
    r = client.post(
        "/api/countdowns", json={"title": "Disney trip", "target_date": "2026-12-20", "icon": "✈️"}
    )
    assert r.status_code == 201
    cid = r.json()["id"]

    rows = client.get("/api/countdowns").json()
    assert [c["title"] for c in rows] == ["Disney trip"]

    assert client.delete(f"/api/countdowns/{cid}").status_code == 204
    assert client.get("/api/countdowns").json() == []
