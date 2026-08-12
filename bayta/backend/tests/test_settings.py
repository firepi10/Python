def test_settings_defaults_and_put(client):
    all_settings = client.get("/api/settings").json()
    assert all_settings["idle_timeout_s"] == 300
    # ships off; a new device must not blank its own screen on night one
    assert all_settings["sleep_schedule"]["enabled"] is False
    assert all_settings["sleep_schedule"]["off"] == "21:30"

    r = client.put("/api/settings/idle_timeout_s", json={"value": 120})
    assert r.status_code == 200
    assert client.get("/api/settings").json()["idle_timeout_s"] == 120

    assert client.put("/api/settings/nope", json={"value": 1}).status_code == 404
