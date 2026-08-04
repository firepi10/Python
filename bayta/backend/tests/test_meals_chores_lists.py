def test_meal_library_and_plan(client):
    r = client.post(
        "/api/meals",
        json={
            "name": "Taco night",
            "icon": "🌮",
            "is_favorite": True,
            "ingredients": ["Tortillas", "Ground beef", "Salsa"],
        },
    )
    assert r.status_code == 201
    meal_id = r.json()["id"]

    meals = client.get("/api/meals").json()
    assert meals[0]["name"] == "Taco night"
    assert meals[0]["ingredients"] == ["Tortillas", "Ground beef", "Salsa"]

    # plan it for Tuesday dinner
    r = client.put(
        "/api/meals/plan", json={"date": "2026-08-11", "slot": "dinner", "meal_id": meal_id}
    )
    assert r.status_code == 200

    plan = client.get("/api/meals/plan", params={"start": "2026-08-10", "end": "2026-08-16"}).json()
    assert plan == [
        {
            "date": "2026-08-11",
            "slot": "dinner",
            "meal_id": meal_id,
            "meal_name": "Taco night",
            "meal_icon": "🌮",
            "custom_text": None,
        }
    ]

    # replace with custom text, then clear
    client.put(
        "/api/meals/plan",
        json={"date": "2026-08-11", "slot": "dinner", "custom_text": "Leftovers"},
    )
    plan = client.get("/api/meals/plan", params={"start": "2026-08-10", "end": "2026-08-16"}).json()
    assert plan[0]["custom_text"] == "Leftovers"

    client.put("/api/meals/plan", json={"date": "2026-08-11", "slot": "dinner"})
    assert (
        client.get("/api/meals/plan", params={"start": "2026-08-10", "end": "2026-08-16"}).json()
        == []
    )


def test_grocery_generation_dedupes(client):
    m1 = client.post(
        "/api/meals", json={"name": "Pasta", "ingredients": ["Pasta", "Tomatoes", "Basil"]}
    ).json()["id"]
    m2 = client.post(
        "/api/meals", json={"name": "Caprese", "ingredients": ["Tomatoes", "Mozzarella", "Basil"]}
    ).json()["id"]
    client.put("/api/meals/plan", json={"date": "2026-08-10", "slot": "dinner", "meal_id": m1})
    client.put("/api/meals/plan", json={"date": "2026-08-11", "slot": "dinner", "meal_id": m2})

    r = client.post("/api/meals/plan/grocery", params={"start": "2026-08-10", "end": "2026-08-16"})
    assert r.json()["added"] == 4  # Pasta, Tomatoes, Basil, Mozzarella (deduped)

    lists = client.get("/api/lists").json()
    grocery = next(x for x in lists if x["kind"] == "grocery")
    assert {i["text"] for i in grocery["items"]} == {"Pasta", "Tomatoes", "Basil", "Mozzarella"}

    # regenerate: nothing new
    r = client.post("/api/meals/plan/grocery", params={"start": "2026-08-10", "end": "2026-08-16"})
    assert r.json()["added"] == 0


def test_chores_due_and_stars(client):
    zoe = client.post("/api/profiles", json={"name": "Zoe", "color": "green"}).json()["id"]

    daily = client.post(
        "/api/chores", json={"title": "Feed the dog", "profile_id": zoe, "points": 2}
    ).json()["id"]
    client.post(
        "/api/chores",
        json={
            "title": "Take out trash",
            "profile_id": zoe,
            "rrule": "FREQ=WEEKLY;BYDAY=TH",
            "points": 5,
        },
    )
    assert (
        client.post("/api/chores", json={"title": "Bad", "rrule": "NOT-A-RULE"}).status_code == 422
    )

    # 2026-08-10 is a Monday: only the daily chore is due
    monday = client.get("/api/chores", params={"day": "2026-08-10"}).json()
    assert [c["title"] for c in monday] == ["Feed the dog"]
    assert monday[0]["completed"] is False

    # 2026-08-13 is a Thursday: both due
    thursday = client.get("/api/chores", params={"day": "2026-08-13"}).json()
    assert {c["title"] for c in thursday} == {"Feed the dog", "Take out trash"}

    # complete + toggle back + complete again
    r = client.post(f"/api/chores/{daily}/complete", json={"date": "2026-08-10"})
    assert r.json()["completed"] is True
    r = client.post(f"/api/chores/{daily}/complete", json={"date": "2026-08-10"})
    assert r.json()["completed"] is False
    client.post(f"/api/chores/{daily}/complete", json={"date": "2026-08-10"})

    stars = client.get("/api/chores/stars", params={"since": "2026-08-09"}).json()
    assert stars == [{"profile_id": zoe, "points": 2}]


def test_lists_crud(client):
    lists = client.get("/api/lists").json()
    assert {x["name"] for x in lists} == {"Groceries", "To-Do"}  # defaults auto-created

    todo = next(x for x in lists if x["kind"] == "todo")
    item = client.post(f"/api/lists/{todo['id']}/items", json={"text": "Fix the gate"}).json()

    client.patch(f"/api/lists/items/{item['id']}", json={"done": True})
    lists = client.get("/api/lists").json()
    todo = next(x for x in lists if x["kind"] == "todo")
    assert todo["items"][0]["done"] is True

    r = client.post(f"/api/lists/{todo['id']}/clear-done")
    assert r.json()["removed"] == 1

    custom = client.post("/api/lists", json={"name": "Hardware store", "icon": "🔨"}).json()
    assert client.delete(f"/api/lists/{custom['id']}").status_code == 204
