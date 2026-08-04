"""Photo ingestion pipeline.

Every photo — phone upload or iCloud Shared Album download — flows through
ingest_bytes: sha256 dedupe, EXIF orientation fix, then three renditions:
  originals/<sha>.<ext>   untouched bytes
  display/<sha>.jpg       long edge 2560px, progressive q85 (screensaver)
  thumbs/<sha>.webp       512px q70 (admin grid)
Paths are stored relative to the photos dir so the data dir can relocate.
"""

import hashlib
import io
import logging
from datetime import UTC, datetime

import pillow_heif
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.events import bus
from app.db.models import Photo

logger = logging.getLogger(__name__)

pillow_heif.register_heif_opener()

DISPLAY_EDGE = 2560
THUMB_EDGE = 512

EXT_BY_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "HEIF": ".heic", "WEBP": ".webp"}


class NotAnImage(Exception):
    pass


def _exif_taken_at(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        raw = exif.get(36867) or exif.get(306)  # DateTimeOriginal, fallback DateTime
        if raw:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
    except Exception:
        pass
    return None


def ingest_bytes(
    db: Session,
    data: bytes,
    *,
    source: str = "upload",
    source_guid: str | None = None,
) -> Photo | None:
    """Returns the created Photo, or None when it was a duplicate."""
    sha = hashlib.sha256(data).hexdigest()
    if db.query(Photo).filter(Photo.sha256 == sha).one_or_none() is not None:
        return None
    if source_guid and db.query(Photo).filter(Photo.source_guid == source_guid).one_or_none():
        return None

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise NotAnImage(str(exc)) from exc

    fmt = img.format or "JPEG"
    taken_at = _exif_taken_at(img)
    img = ImageOps.exif_transpose(img)

    photos_dir = get_settings().photos_dir
    for sub in ("originals", "display", "thumbs"):
        (photos_dir / sub).mkdir(parents=True, exist_ok=True)

    original_rel = f"originals/{sha}{EXT_BY_FORMAT.get(fmt, '.jpg')}"
    (photos_dir / original_rel).write_bytes(data)

    display = img.convert("RGB")
    display.thumbnail((DISPLAY_EDGE, DISPLAY_EDGE))
    display_rel = f"display/{sha}.jpg"
    display.save(photos_dir / display_rel, "JPEG", quality=85, progressive=True)

    thumb = img.convert("RGB")
    thumb.thumbnail((THUMB_EDGE, THUMB_EDGE))
    thumb_rel = f"thumbs/{sha}.webp"
    thumb.save(photos_dir / thumb_rel, "WEBP", quality=70)

    photo = Photo(
        sha256=sha,
        original_path=original_rel,
        display_path=display_rel,
        thumb_path=thumb_rel,
        width=display.width,
        height=display.height,
        taken_at=taken_at,
        source=source,
        source_guid=source_guid,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    bus.publish("photos")
    return photo


def delete_photo(db: Session, photo: Photo) -> None:
    photos_dir = get_settings().photos_dir
    for rel in (photo.original_path, photo.display_path, photo.thumb_path):
        try:
            (photos_dir / rel).unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("could not remove %s: %s", rel, exc)
    db.delete(photo)
    db.commit()
    bus.publish("photos")
