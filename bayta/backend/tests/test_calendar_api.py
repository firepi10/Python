from app.db.models import PendingOp


def test_event_lifecycle_local_only(client, db):
    r = client.post(
        "/api/calendar/events",
        json={
            "summary": "Date night",
            "start": "2026-08-14T23:00:00Z",
            "end": "2026-08-15T01:00:00Z",
        },
    )
    assert r.status_code == 201
    event_id = r.json()["id"]

    occs = client.get(
        "/api/calendar/occurrences",
        params={"start": "2026-08-14T00:00:00Z", "end": "2026-08-16T00:00:00Z"},
    ).json()
    assert len(occs) == 1
    assert occs[0]["summary"] == "Date night"
    assert occs[0]["calendar_name"] == "Bayta"

    # local-only events (no CalDAV calendar) must NOT enqueue push ops
    assert db.query(PendingOp).count() == 0

    r = client.patch(
        f"/api/calendar/events/{event_id}",
        json={
            "summary": "Date night (moved)",
            "start": "2026-08-15T23:00:00Z",
            "end": "2026-08-16T01:00:00Z",
        },
    )
    assert r.status_code == 200

    occs = client.get(
        "/api/calendar/occurrences",
        params={"start": "2026-08-14T00:00:00Z", "end": "2026-08-17T00:00:00Z"},
    ).json()
    assert [o["summary"] for o in occs] == ["Date night (moved)"]

    assert client.delete(f"/api/calendar/events/{event_id}").status_code == 204
    occs = client.get(
        "/api/calendar/occurrences",
        params={"start": "2026-08-14T00:00:00Z", "end": "2026-08-17T00:00:00Z"},
    ).json()
    assert occs == []


def test_recurring_event_expands(client):
    r = client.post(
        "/api/calendar/events",
        json={
            "summary": "Piano lesson",
            "start": "2026-08-05T20:00:00Z",
            "end": "2026-08-05T20:45:00Z",
            "rrule": "FREQ=WEEKLY;BYDAY=WE",
        },
    )
    assert r.status_code == 201

    occs = client.get(
        "/api/calendar/occurrences",
        params={"start": "2026-08-01T00:00:00Z", "end": "2026-08-31T00:00:00Z"},
    ).json()
    assert len(occs) == 4
    assert all(o["is_recurring"] for o in occs)


def test_validation_rejects_reversed_times(client):
    r = client.post(
        "/api/calendar/events",
        json={
            "summary": "Backwards",
            "start": "2026-08-14T23:00:00Z",
            "end": "2026-08-14T22:00:00Z",
        },
    )
    assert r.status_code == 422
