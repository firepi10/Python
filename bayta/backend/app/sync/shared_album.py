"""iCloud Shared Album ingestion.

Public shared albums expose an unauthenticated JSON API (the same one the
icloud.com web viewer uses): POST .../{token}/sharedstreams/webstream lists
photo GUIDs + derivative checksums; POST .../webasseturls signs CDN URLs.
No Apple ID, no 2FA, and the link never expires unless sharing is turned
off — which is why this is Bayta's primary photo pipe.

A 330 response means "wrong partition": the body names the correct
X-Apple-MMe-Host, which we cache on the album row.
"""

import logging
import re
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.db.models import SharedAlbum
from app.db.session import session_factory
from app.services.photo_service import NotAnImage, ingest_bytes

logger = logging.getLogger(__name__)

DEFAULT_HOST = "p23-sharedstreams.icloud.com"


def parse_share_url(url: str) -> str | None:
    """https://www.icloud.com/sharedalbum/#B0abcDEFGgHIJK -> B0abcDEFGgHIJK"""
    m = re.search(r"#([A-Za-z0-9_-]{8,})", url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{8,}", url.strip()):
        return url.strip()
    return None


def _base(host: str, token: str) -> str:
    return f"https://{host}/{token}/sharedstreams"


def fetch_stream(
    client: httpx.Client, token: str, host: str | None
) -> tuple[str, dict]:
    """Returns (host, webstream payload), following the 330 partition hop."""
    host = host or DEFAULT_HOST
    for _ in range(2):
        resp = client.post(f"{_base(host, token)}/webstream", json={"streamCtag": None})
        if resp.status_code == 330:
            host = resp.json().get("X-Apple-MMe-Host", host)
            continue
        resp.raise_for_status()
        return host, resp.json()
    raise RuntimeError("shared album: too many partition redirects")


def fetch_asset_urls(client: httpx.Client, token: str, host: str, guids: list[str]) -> dict:
    resp = client.post(f"{_base(host, token)}/webasseturls", json={"photoGuids": guids})
    resp.raise_for_status()
    return resp.json().get("items", {})


def best_derivative(photo: dict) -> dict | None:
    derivatives = photo.get("derivatives") or {}
    best = None
    best_h = -1
    for key, deriv in derivatives.items():
        try:
            h = int(key)
        except ValueError:
            h = 0
        if h > best_h:
            best_h, best = h, deriv
    return best


def sync_album(db: Session, album: SharedAlbum, client: httpx.Client) -> int:
    host, payload = fetch_stream(client, album.token, album.base_host)
    album.base_host = host
    album.name = payload.get("streamName") or album.name

    from app.db.models import Photo

    known = {
        guid
        for (guid,) in db.query(Photo.source_guid).filter(Photo.source_guid.isnot(None)).all()
    }
    photos = payload.get("photos") or []
    new_photos = [p for p in photos if p.get("photoGuid") and p["photoGuid"] not in known]
    if not new_photos:
        album.last_sync_at = datetime.now(UTC)
        db.commit()
        return 0

    assets = fetch_asset_urls(
        client, album.token, host, [p["photoGuid"] for p in new_photos]
    )

    added = 0
    for photo in new_photos:
        deriv = best_derivative(photo)
        if not deriv:
            continue
        item = assets.get(deriv.get("checksum", ""))
        if not item:
            continue
        url = f"https://{item['url_location']}{item['url_path']}"
        try:
            resp = client.get(url)
            resp.raise_for_status()
            if ingest_bytes(
                db, resp.content, source="shared_album", source_guid=photo["photoGuid"]
            ):
                added += 1
        except NotAnImage:
            logger.info("skipping non-image asset %s (video?)", photo["photoGuid"])
        except Exception as exc:
            logger.warning("failed downloading %s: %s", photo["photoGuid"], exc)

    album.last_sync_at = datetime.now(UTC)
    album.last_error = None
    db.commit()
    return added


def sync_shared_albums(client: httpx.Client | None = None) -> int:
    """Scheduler entrypoint (30-min interval)."""
    db = session_factory()()
    own = client is None
    c = client or httpx.Client(timeout=60, follow_redirects=True)
    total = 0
    try:
        for album in db.query(SharedAlbum).filter(SharedAlbum.enabled.is_(True)).all():
            try:
                total += sync_album(db, album, c)
            except Exception as exc:
                db.rollback()
                album.last_error = str(exc)[:500]
                db.commit()
                logger.exception("shared album %s sync failed", album.token)
    finally:
        if own:
            c.close()
        db.close()
    return total
