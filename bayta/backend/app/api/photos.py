import random

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Photo, SharedAlbum
from app.db.session import get_db
from app.services import photo_service
from app.sync import shared_album as shared_album_sync

router = APIRouter(prefix="/photos", tags=["photos"])


def _photo_dict(p: Photo) -> dict:
    return {
        "id": p.id,
        "url": f"/media/photos/{p.display_path}",
        "thumb": f"/media/photos/{p.thumb_path}",
        "width": p.width,
        "height": p.height,
        "source": p.source,
        "hidden": p.hidden,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "created_at": p.created_at.isoformat(),
    }


@router.get("")
def list_photos(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(Photo)
        .order_by(Photo.created_at.desc())
        .offset(offset)
        .limit(min(limit, 500))
        .all()
    )
    return [_photo_dict(p) for p in rows]


@router.post("/upload", status_code=201)
async def upload(files: list[UploadFile], db: Session = Depends(get_db)) -> dict:
    added, duplicates, failed = 0, 0, 0
    for file in files:
        data = await file.read()
        try:
            photo = await run_in_threadpool(photo_service.ingest_bytes, db, data)
        except photo_service.NotAnImage:
            failed += 1
            continue
        if photo is None:
            duplicates += 1
        else:
            added += 1
    return {"added": added, "duplicates": duplicates, "failed": failed}


@router.get("/slideshow")
def slideshow(limit: int = 40, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(Photo).filter(Photo.hidden.is_(False)).all()
    random.shuffle(rows)
    return [
        {"url": f"/media/photos/{p.display_path}", "width": p.width, "height": p.height}
        for p in rows[: min(limit, 100)]
    ]


@router.patch("/{photo_id}")
def patch_photo(photo_id: int, body: dict, db: Session = Depends(get_db)) -> dict:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(404, "photo not found")
    if "hidden" in body:
        photo.hidden = bool(body["hidden"])
    db.commit()
    return _photo_dict(photo)


@router.delete("/{photo_id}", status_code=204)
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(404, "photo not found")
    photo_service.delete_photo(db, photo)


# ------------------------------------------------------------ shared albums


class SharedAlbumIn(BaseModel):
    url: str


@router.get("/shared-albums")
def list_albums(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": a.id,
            "name": a.name or "Shared album",
            "enabled": a.enabled,
            "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
            "last_error": a.last_error,
        }
        for a in db.query(SharedAlbum).all()
    ]


@router.post("/shared-albums", status_code=201)
async def add_album(body: SharedAlbumIn, db: Session = Depends(get_db)) -> dict:
    token = shared_album_sync.parse_share_url(body.url)
    if token is None:
        raise HTTPException(
            422,
            "That doesn't look like an iCloud shared album link. In Photos, open the "
            "album → share icon → Copy iCloud Link, and paste the whole link here.",
        )
    if db.query(SharedAlbum).filter(SharedAlbum.token == token).one_or_none():
        raise HTTPException(409, "This album is already connected.")
    album = SharedAlbum(token=token)
    db.add(album)
    db.commit()
    added = await run_in_threadpool(shared_album_sync.sync_shared_albums)
    db.refresh(album)
    if album.last_error:
        detail = album.last_error
        db.delete(album)
        db.commit()
        raise HTTPException(502, f"Could not read that album: {detail}")
    return {"id": album.id, "name": album.name, "added": added}


@router.delete("/shared-albums/{album_id}", status_code=204)
def delete_album(album_id: int, db: Session = Depends(get_db)):
    album = db.get(SharedAlbum, album_id)
    if album is None:
        raise HTTPException(404, "album not found")
    db.delete(album)
    db.commit()


@router.post("/shared-albums/sync-now")
async def sync_albums_now() -> dict:
    added = await run_in_threadpool(shared_album_sync.sync_shared_albums)
    return {"added": added}
