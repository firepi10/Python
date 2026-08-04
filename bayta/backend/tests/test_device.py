from datetime import datetime

from app.services.sleep_service import should_be_asleep


def test_sleep_window_wraps_midnight():
    off, on = "21:30", "06:30"
    assert should_be_asleep(datetime(2026, 8, 4, 23, 0), off, on) is True
    assert should_be_asleep(datetime(2026, 8, 4, 2, 0), off, on) is True
    assert should_be_asleep(datetime(2026, 8, 4, 6, 29), off, on) is True
    assert should_be_asleep(datetime(2026, 8, 4, 6, 30), off, on) is False
    assert should_be_asleep(datetime(2026, 8, 4, 12, 0), off, on) is False
    assert should_be_asleep(datetime(2026, 8, 4, 21, 29), off, on) is False
    assert should_be_asleep(datetime(2026, 8, 4, 21, 30), off, on) is True


def test_sleep_window_same_day_and_degenerate():
    assert should_be_asleep(datetime(2026, 8, 4, 13, 0), "12:00", "14:00") is True
    assert should_be_asleep(datetime(2026, 8, 4, 15, 0), "12:00", "14:00") is False
    assert should_be_asleep(datetime(2026, 8, 4, 12, 0), "12:00", "12:00") is False


def test_device_endpoints(client):
    info = client.get("/api/device").json()
    assert info["version"]
    assert info["disk_total_gb"] > 0
    assert "display_on" in info

    # display tools absent in the dev container -> ops report gracefully
    assert client.post("/api/device/sleep").status_code == 200
    assert client.post("/api/device/wake").status_code == 200

    r = client.put("/api/device/rotation", json={"transform": "90"})
    assert r.status_code == 200
    assert r.json()["applied_live"] is False  # no wlr-randr here

    assert client.put("/api/device/rotation", json={"transform": "45"}).status_code == 422
    assert client.post("/api/device/reload-ui").json() == {"ok": True}
