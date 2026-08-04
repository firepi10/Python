def test_profile_crud(client):
    assert client.get("/api/profiles").json() == []

    r = client.post("/api/profiles", json={"name": "Zoe", "color": "green"})
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.post("/api/profiles", json={"name": "Bad", "color": "mauve"})
    assert r.status_code == 422

    r = client.patch(f"/api/profiles/{pid}", json={"name": "Zoe K", "color": "teal"})
    assert r.status_code == 200
    assert r.json()["name"] == "Zoe K"

    assert len(client.get("/api/profiles").json()) == 1

    assert client.delete(f"/api/profiles/{pid}").status_code == 204
    assert client.get("/api/profiles").json() == []
