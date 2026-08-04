from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.events import bus
from app.db.models import ListItem, ListModel
from app.db.session import get_db

router = APIRouter(prefix="/lists", tags=["lists"])


class ListIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = "custom"
    icon: str | None = None


class ItemIn(BaseModel):
    text: str = Field(min_length=1, max_length=255)


class ItemPatch(BaseModel):
    text: str | None = None
    done: bool | None = None


def _list_dict(lst: ListModel) -> dict:
    return {
        "id": lst.id,
        "name": lst.name,
        "kind": lst.kind,
        "icon": lst.icon,
        "items": [
            {"id": i.id, "text": i.text, "done": i.done}
            for i in sorted(lst.items, key=lambda x: (x.done, x.sort_order, x.id))
        ],
    }


def _ensure_defaults(db: Session) -> None:
    if db.query(ListModel).count() == 0:
        db.add(ListModel(name="Groceries", kind="grocery", icon="🛒", sort_order=0))
        db.add(ListModel(name="To-Do", kind="todo", icon="✅", sort_order=1))
        db.commit()


@router.get("")
def get_lists(db: Session = Depends(get_db)) -> list[dict]:
    _ensure_defaults(db)
    lists = (
        db.query(ListModel).options(joinedload(ListModel.items)).order_by(ListModel.sort_order).all()
    )
    return [_list_dict(x) for x in lists]


@router.post("", status_code=201)
def create_list(body: ListIn, db: Session = Depends(get_db)) -> dict:
    if body.kind not in ("grocery", "todo", "custom"):
        raise HTTPException(422, "kind must be grocery, todo or custom")
    lst = ListModel(**body.model_dump(), sort_order=db.query(ListModel).count())
    db.add(lst)
    db.commit()
    db.refresh(lst)
    bus.publish("lists")
    return _list_dict(lst)


@router.delete("/{list_id}", status_code=204)
def delete_list(list_id: int, db: Session = Depends(get_db)):
    lst = db.get(ListModel, list_id)
    if lst is None:
        raise HTTPException(404, "list not found")
    db.delete(lst)
    db.commit()
    bus.publish("lists")


@router.post("/{list_id}/items", status_code=201)
def add_item(list_id: int, body: ItemIn, db: Session = Depends(get_db)) -> dict:
    lst = db.get(ListModel, list_id)
    if lst is None:
        raise HTTPException(404, "list not found")
    item = ListItem(list_id=list_id, text=body.text, sort_order=len(lst.items))
    db.add(item)
    db.commit()
    bus.publish("lists")
    return {"id": item.id, "text": item.text, "done": item.done}


@router.patch("/items/{item_id}")
def patch_item(item_id: int, body: ItemPatch, db: Session = Depends(get_db)) -> dict:
    item = db.get(ListItem, item_id)
    if item is None:
        raise HTTPException(404, "item not found")
    if body.text is not None:
        item.text = body.text
    if body.done is not None:
        item.done = body.done
        item.done_at = datetime.now(UTC) if body.done else None
    db.commit()
    bus.publish("lists")
    return {"id": item.id, "text": item.text, "done": item.done}


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ListItem, item_id)
    if item is None:
        raise HTTPException(404, "item not found")
    db.delete(item)
    db.commit()
    bus.publish("lists")


@router.post("/{list_id}/clear-done", status_code=200)
def clear_done(list_id: int, db: Session = Depends(get_db)) -> dict:
    lst = db.get(ListModel, list_id)
    if lst is None:
        raise HTTPException(404, "list not found")
    removed = (
        db.query(ListItem).filter(ListItem.list_id == list_id, ListItem.done.is_(True)).delete()
    )
    db.commit()
    bus.publish("lists")
    return {"removed": removed}
