import httpx


def test_weather_sync_and_endpoint(client):
    assert client.get("/api/weather").json() == {"available": False}

    fake = {
        "current": {"temperature_2m": 74.1, "weather_code": 1, "is_day": 1},
        "daily": {
            "time": ["2026-08-04"],
            "weather_code": [1],
            "temperature_2m_max": [82.0],
            "temperature_2m_min": [66.0],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.open-meteo.com"
        return httpx.Response(200, json=fake)

    from app.sync.weather_sync import sync_weather

    payload = sync_weather(client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert payload == fake

    body = client.get("/api/weather").json()
    assert body["available"] is True
    assert body["data"]["current"]["temperature_2m"] == 74.1
