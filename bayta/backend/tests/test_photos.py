import io

import httpx
from PIL import Image

from app.db.models import Photo, SharedAlbum


def _jpeg_bytes(w=3000, h=2000, color=(200, 120, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


def _heic_bytes(w=1200, h=900) -> bytes:
    import pillow_heif

    heif = pillow_heif.from_pillow(Image.new("RGB", (w, h), (30, 90, 200)))
    buf = io.BytesIO()
    heif.save(buf, format="HEIF")
    return buf.getvalue()


def test_upload_pipeline_and_dedupe(client):
    data = _jpeg_bytes()
    r = client.post("/api/photos/upload", files=[("files", ("a.jpg", data, "image/jpeg"))])
    assert r.status_code == 201
    assert r.json() == {"added": 1, "duplicates": 0, "failed": 0}

    # same bytes again -> dedupe
    r = client.post("/api/photos/upload", files=[("files", ("b.jpg", data, "image/jpeg"))])
    assert r.json() == {"added": 0, "duplicates": 1, "failed": 0}

    photos = client.get("/api/photos").json()
    assert len(photos) == 1
    p = photos[0]
    assert p["width"] == 2560 and p["height"] == 1707  # display rendition resized

    # renditions are actually served
    assert client.get(p["url"]).status_code == 200
    assert client.get(p["thumb"]).status_code == 200

    # slideshow feed
    slides = client.get("/api/photos/slideshow").json()
    assert len(slides) == 1

    # junk upload is rejected gracefully
    junk = [("files", ("x.jpg", b"not an image", "image/jpeg"))]
    r = client.post("/api/photos/upload", files=junk)
    assert r.json()["failed"] == 1


def test_heic_upload(client):
    r = client.post(
        "/api/photos/upload", files=[("files", ("iphone.heic", _heic_bytes(), "image/heic"))]
    )
    assert r.json()["added"] == 1
    p = client.get("/api/photos").json()[0]
    assert p["url"].endswith(".jpg")  # HEIC transcoded for the browser


def test_delete_removes_files(client, db):
    small = [("files", ("a.jpg", _jpeg_bytes(800, 600), "image/jpeg"))]
    client.post("/api/photos/upload", files=small)
    photo = db.query(Photo).one()

    from app.core.config import get_settings

    display = get_settings().photos_dir / photo.display_path
    assert display.exists()
    assert client.delete(f"/api/photos/{photo.id}").status_code == 204
    assert not display.exists()
    assert client.get("/api/photos").json() == []


def _album_transport(image_bytes: bytes) -> httpx.MockTransport:
    """Fake iCloud shared-album service incl. the 330 partition redirect."""
    state = {"webstream_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/webstream"):
            state["webstream_calls"] += 1
            if request.url.host.startswith("p23-"):
                host = {"X-Apple-MMe-Host": "p42-sharedstreams.icloud.com"}
                return httpx.Response(330, json=host)
            return httpx.Response(
                200,
                json={
                    "streamName": "Family Wall",
                    "photos": [
                        {
                            "photoGuid": "guid-1",
                            "derivatives": {
                                "342": {"checksum": "small-1"},
                                "2048": {"checksum": "big-1"},
                            },
                        },
                        {
                            "photoGuid": "guid-2",
                            "derivatives": {"1024": {"checksum": "big-2"}},
                        },
                    ],
                },
            )
        if request.url.path.endswith("/webasseturls"):
            return httpx.Response(
                200,
                json={
                    "items": {
                        "big-1": {"url_location": "cdn.icloud.example", "url_path": "/a1.jpg"},
                        "big-2": {"url_location": "cdn.icloud.example", "url_path": "/a2.jpg"},
                    }
                },
            )
        if request.url.host == "cdn.icloud.example":
            return httpx.Response(200, content=image_bytes)
        return httpx.Response(404)

    return httpx.MockTransport(handler), state


def test_shared_album_sync(client, db):
    transport, state = _album_transport(_jpeg_bytes(1600, 1200))
    album = SharedAlbum(token="B0testTOKEN123")
    db.add(album)
    db.commit()

    from app.sync.shared_album import sync_shared_albums

    added = sync_shared_albums(client=httpx.Client(transport=transport))
    assert added == 1  # two guids, identical bytes -> one photo + one dedupe

    db.expire_all()
    album = db.query(SharedAlbum).one()
    assert album.base_host == "p42-sharedstreams.icloud.com"  # 330 redirect honored
    assert album.name == "Family Wall"
    assert album.last_sync_at is not None

    photos = db.query(Photo).all()
    assert {p.source for p in photos} == {"shared_album"}

    # second run: all guids known -> no downloads
    added = sync_shared_albums(client=httpx.Client(transport=transport))
    assert added == 0


def test_share_url_parsing(client):
    r = client.post("/api/photos/shared-albums", json={"url": "https://example.com/nope"})
    assert r.status_code == 422
