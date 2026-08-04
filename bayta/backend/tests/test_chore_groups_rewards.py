def _mk_profiles(client):
    lainey = client.post("/api/profiles", json={"name": "Lainey", "color": "purple"}).json()["id"]
    charlee = client.post("/api/profiles", json={"name": "Charlee", "color": "green"}).json()["id"]
    return lainey, charlee


def test_shared_chore_expands_per_person(client):
    lainey, charlee = _mk_profiles(client)
    chore = client.post(
        "/api/chores",
        json={"title": "Empty dishwasher", "profile_ids": [lainey, charlee], "points": 2},
    ).json()
    assert chore["profile_ids"] == sorted([lainey, charlee])

    day = client.get("/api/chores", params={"day": "2026-08-10"}).json()
    assert len(day) == 2  # one row per girl
    assert all(c["shared"] for c in day)
    assert {c["profile_id"] for c in day} == {lainey, charlee}

    # Lainey checks off HER copy; Charlee's stays open
    client.post(
        f"/api/chores/{chore['id']}/complete",
        json={"date": "2026-08-10", "profile_id": lainey},
    )
    day = client.get("/api/chores", params={"day": "2026-08-10"}).json()
    by_person = {c["profile_id"]: c["completed"] for c in day}
    assert by_person[lainey] is True
    assert by_person[charlee] is False

    # someone not assigned can't check it off
    other = client.post("/api/profiles", json={"name": "Sunnie", "color": "yellow"}).json()["id"]
    r = client.post(
        f"/api/chores/{chore['id']}/complete",
        json={"date": "2026-08-10", "profile_id": other},
    )
    assert r.status_code == 422

    # each girl earns her own stars
    client.post(
        f"/api/chores/{chore['id']}/complete",
        json={"date": "2026-08-10", "profile_id": charlee},
    )
    stars = {
        s["profile_id"]: s["points"]
        for s in client.get("/api/chores/stars", params={"since": "2026-08-09"}).json()
    }
    assert stars == {lainey: 2, charlee: 2}


def test_everyone_chore_single_checkbox(client):
    chore = client.post("/api/chores", json={"title": "Tidy living room"}).json()
    day = client.get("/api/chores", params={"day": "2026-08-10"}).json()
    assert len(day) == 1
    assert day[0]["profile_id"] is None and day[0]["shared"] is False

    r = client.post(f"/api/chores/{chore['id']}/complete", json={"date": "2026-08-10"})
    assert r.json()["completed"] is True


def test_rewards_store_and_claiming(client):
    lainey, charlee = _mk_profiles(client)
    chore = client.post(
        "/api/chores", json={"title": "Beds", "profile_ids": [lainey, charlee], "points": 5}
    ).json()

    movie = client.post(
        "/api/rewards", json={"title": "Movie night pick", "icon": "🎬", "cost_points": 10}
    ).json()
    assert movie["cost_points"] == 10

    # Lainey earns 15 stars over three days; Charlee earns 5
    for d in ("2026-08-10", "2026-08-11", "2026-08-12"):
        client.post(f"/api/chores/{chore['id']}/complete", json={"date": d, "profile_id": lainey})
    client.post(
        f"/api/chores/{chore['id']}/complete", json={"date": "2026-08-10", "profile_id": charlee}
    )

    balances = {b["profile_id"]: b for b in client.get("/api/rewards").json()["balances"]}
    assert balances[lainey]["balance"] == 15
    assert balances[charlee]["balance"] == 5

    # Charlee can't afford it yet — friendly error says how many more stars
    r = client.post(f"/api/rewards/{movie['id']}/claim", json={"profile_id": charlee})
    assert r.status_code == 422
    assert "5 more stars" in r.json()["detail"]

    # Lainey claims it: stars are spent
    r = client.post(f"/api/rewards/{movie['id']}/claim", json={"profile_id": lainey})
    assert r.status_code == 200
    assert r.json()["balance"] == 5

    balances = {b["profile_id"]: b for b in client.get("/api/rewards").json()["balances"]}
    assert balances[lainey] == {"profile_id": lainey, "earned": 15, "spent": 10, "balance": 5}

    history = client.get("/api/rewards/claims").json()
    assert history[0]["reward"] == "Movie night pick"
    assert history[0]["profile_id"] == lainey

    # un-completing a day claws the stars back
    client.post(
        f"/api/chores/{chore['id']}/complete", json={"date": "2026-08-12", "profile_id": lainey}
    )
    balances = {b["profile_id"]: b for b in client.get("/api/rewards").json()["balances"]}
    assert balances[lainey]["balance"] == 0
