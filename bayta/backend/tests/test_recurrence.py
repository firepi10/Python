"""Recurrence coverage for the frequencies the UI actually offers, plus the
edit path that used to silently destroy a series."""

from datetime import UTC, datetime, timedelta

from app.services.ics import build_event_ics, new_uid, parse_event_ics
from app.sync.ics_expand import WINDOW_FUTURE_DAYS, expand_ics


def test_yearly_birthday_repeats_on_the_date_not_weekly():
    ics = build_event_ics(
        uid=new_uid(),
        summary="Sunnie's birthday",
        dtstart=datetime(2026, 8, 24, tzinfo=UTC).date(),
        dtend=datetime(2026, 8, 25, tzinfo=UTC).date(),
        all_day=True,
        rrule="FREQ=YEARLY",
    )
    assert parse_event_ics(ics)["rrule"] == "FREQ=YEARLY"

    occs = expand_ics(
        ics, datetime(2026, 8, 1, tzinfo=UTC), datetime(2029, 1, 1, tzinfo=UTC)
    )
    starts = [o[0].date().isoformat() for o in occs]
    assert starts == ["2026-08-24", "2027-08-24", "2028-08-24"]

    # the reported bug: no weekly copies in the weeks after the first one
    assert "2026-08-31" not in starts
    assert "2026-09-07" not in starts


def test_yearly_next_occurrence_fits_the_cached_window():
    """A birthday must still be visible a year out with the default window."""
    start = datetime(2026, 3, 2, tzinfo=UTC)
    ics = build_event_ics(
        uid=new_uid(),
        summary="Anniversary",
        dtstart=start.date(),
        dtend=(start + timedelta(days=1)).date(),
        all_day=True,
        rrule="FREQ=YEARLY",
    )
    occs = expand_ics(ics, start, start + timedelta(days=WINDOW_FUTURE_DAYS))
    assert len(occs) >= 2
    assert occs[1][0].date().isoformat() == "2027-03-02"


def test_monthly_repeats_by_date():
    ics = build_event_ics(
        uid=new_uid(),
        summary="Rent",
        dtstart=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
        dtend=datetime(2026, 1, 5, 9, 30, tzinfo=UTC),
        all_day=False,
        rrule="FREQ=MONTHLY",
    )
    occs = expand_ics(
        ics, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC)
    )
    assert [o[0].date().isoformat() for o in occs] == [
        "2026-01-05",
        "2026-02-05",
        "2026-03-05",
        "2026-04-05",
        "2026-05-05",
        "2026-06-05",
    ]


def _yearly_payload(**overrides) -> dict:
    body = {
        "summary": "Sunnie's birthday",
        "start": "2026-08-24T00:00:00Z",
        "end": "2026-08-25T00:00:00Z",
        "all_day": True,
        "rrule": "FREQ=YEARLY",
    }
    body.update(overrides)
    return body


def test_api_yearly_event_lands_on_next_years_date(client):
    assert client.post("/api/calendar/events", json=_yearly_payload()).status_code == 201

    this_year = client.get(
        "/api/calendar/occurrences",
        params={"start": "2026-08-01T00:00:00Z", "end": "2026-09-01T00:00:00Z"},
    ).json()
    assert len(this_year) == 1
    assert this_year[0]["rrule"] == "FREQ=YEARLY"

    next_year = client.get(
        "/api/calendar/occurrences",
        params={"start": "2027-08-01T00:00:00Z", "end": "2027-09-01T00:00:00Z"},
    ).json()
    assert [o["start"][:10] for o in next_year] == ["2027-08-24"]

    # and nothing in the weeks in between (the bug the user hit)
    following_week = client.get(
        "/api/calendar/occurrences",
        params={"start": "2026-08-30T00:00:00Z", "end": "2026-09-02T00:00:00Z"},
    ).json()
    assert following_week == []


def test_editing_an_event_keeps_its_repeat(client):
    event_id = client.post("/api/calendar/events", json=_yearly_payload()).json()["id"]

    # the frontend now sends the rule back; a rename must not flatten the series
    r = client.patch(
        f"/api/calendar/events/{event_id}",
        json=_yearly_payload(summary="Sunnie's 3rd birthday"),
    )
    assert r.status_code == 200

    detail = client.get(f"/api/calendar/events/{event_id}").json()
    assert detail["summary"] == "Sunnie's 3rd birthday"
    assert detail["is_recurring"] is True
    assert detail["rrule"] == "FREQ=YEARLY"

    next_year = client.get(
        "/api/calendar/occurrences",
        params={"start": "2027-08-01T00:00:00Z", "end": "2027-09-01T00:00:00Z"},
    ).json()
    assert len(next_year) == 1


def test_patch_without_rrule_field_preserves_recurrence(client):
    """An API client that omits rrule entirely must not strip the series."""
    event_id = client.post("/api/calendar/events", json=_yearly_payload()).json()["id"]

    body = _yearly_payload(summary="Renamed")
    del body["rrule"]
    assert client.patch(f"/api/calendar/events/{event_id}", json=body).status_code == 200

    detail = client.get(f"/api/calendar/events/{event_id}").json()
    assert detail["is_recurring"] is True
    assert detail["rrule"] == "FREQ=YEARLY"


def test_patch_can_change_or_clear_the_repeat(client):
    event_id = client.post("/api/calendar/events", json=_yearly_payload()).json()["id"]

    client.patch(
        f"/api/calendar/events/{event_id}", json=_yearly_payload(rrule="FREQ=MONTHLY")
    )
    assert client.get(f"/api/calendar/events/{event_id}").json()["rrule"] == "FREQ=MONTHLY"

    client.patch(f"/api/calendar/events/{event_id}", json=_yearly_payload(rrule=None))
    detail = client.get(f"/api/calendar/events/{event_id}").json()
    assert detail["rrule"] is None
    assert detail["is_recurring"] is False


def test_invalid_repeat_rule_is_rejected_clearly(client):
    for bad in ("NOT-A-RULE", "FREQ=BOGUS"):
        r = client.post("/api/calendar/events", json=_yearly_payload(rrule=bad))
        assert r.status_code == 422, f"{bad} should be refused"
        assert "repeat rule" in r.json()["detail"]


def test_occurrences_past_the_cache_are_expanded_on_demand(client):
    """Scrolling years ahead still shows a yearly birthday."""
    client.post("/api/calendar/events", json=_yearly_payload())
    far = client.get(
        "/api/calendar/occurrences",
        params={"start": "2031-08-01T00:00:00Z", "end": "2031-09-01T00:00:00Z"},
    ).json()
    assert [o["start"][:10] for o in far] == ["2031-08-24"]
    assert far[0]["summary"] == "Sunnie's birthday"
