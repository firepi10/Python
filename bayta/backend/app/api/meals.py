from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.events import bus
from app.db.models import ListItem, ListModel, Meal, MealIngredient, MealPlanEntry
from app.db.session import get_db

router = APIRouter(prefix="/meals", tags=["meals"])

SLOTS = ("breakfast", "lunch", "dinner", "snack")


class MealIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    icon: str | None = None
    notes: str | None = None
    recipe_url: str | None = None
    tags: str | None = None
    is_favorite: bool = False
    ingredients: list[str] = []


def _meal_dict(m: Meal) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "icon": m.icon,
        "notes": m.notes,
        "recipe_url": m.recipe_url,
        "tags": m.tags,
        "is_favorite": m.is_favorite,
        "ingredients": [i.text for i in m.ingredients],
    }


@router.get("")
def list_meals(db: Session = Depends(get_db)) -> list[dict]:
    meals = (
        db.query(Meal)
        .options(joinedload(Meal.ingredients))
        .order_by(Meal.is_favorite.desc(), Meal.name)
        .all()
    )
    return [_meal_dict(m) for m in meals]


@router.post("", status_code=201)
def create_meal(body: MealIn, db: Session = Depends(get_db)) -> dict:
    meal = Meal(**body.model_dump(exclude={"ingredients"}))
    db.add(meal)
    db.flush()
    for i, text in enumerate(body.ingredients):
        db.add(MealIngredient(meal_id=meal.id, text=text, sort_order=i))
    db.commit()
    db.refresh(meal)
    bus.publish("meals")
    return _meal_dict(meal)


@router.patch("/{meal_id}")
def update_meal(meal_id: int, body: MealIn, db: Session = Depends(get_db)) -> dict:
    meal = db.get(Meal, meal_id)
    if meal is None:
        raise HTTPException(404, "meal not found")
    for k, v in body.model_dump(exclude={"ingredients"}).items():
        setattr(meal, k, v)
    db.query(MealIngredient).filter(MealIngredient.meal_id == meal.id).delete()
    for i, text in enumerate(body.ingredients):
        db.add(MealIngredient(meal_id=meal.id, text=text, sort_order=i))
    db.commit()
    db.refresh(meal)
    bus.publish("meals")
    return _meal_dict(meal)


@router.delete("/{meal_id}", status_code=204)
def delete_meal(meal_id: int, db: Session = Depends(get_db)):
    meal = db.get(Meal, meal_id)
    if meal is None:
        raise HTTPException(404, "meal not found")
    db.delete(meal)
    db.commit()
    bus.publish("meals")


# -------------------------------------------------------------------- plan


class PlanIn(BaseModel):
    date: date_type
    slot: str
    meal_id: int | None = None
    custom_text: str | None = None


@router.get("/plan")
def get_plan(
    start: date_type = Query(...), end: date_type = Query(...), db: Session = Depends(get_db)
) -> list[dict]:
    entries = (
        db.query(MealPlanEntry)
        .options(joinedload(MealPlanEntry.meal))
        .filter(MealPlanEntry.date >= start, MealPlanEntry.date <= end)
        .all()
    )
    return [
        {
            "date": e.date.isoformat(),
            "slot": e.slot,
            "meal_id": e.meal_id,
            "meal_name": e.meal.name if e.meal else None,
            "meal_icon": e.meal.icon if e.meal else None,
            "custom_text": e.custom_text,
        }
        for e in entries
    ]


@router.put("/plan")
def put_plan(body: PlanIn, db: Session = Depends(get_db)) -> dict:
    if body.slot not in SLOTS:
        raise HTTPException(422, f"slot must be one of {SLOTS}")
    entry = (
        db.query(MealPlanEntry)
        .filter(MealPlanEntry.date == body.date, MealPlanEntry.slot == body.slot)
        .one_or_none()
    )
    if body.meal_id is None and not body.custom_text:
        if entry is not None:
            db.delete(entry)
        db.commit()
        bus.publish("meals")
        return {"cleared": True}
    if body.meal_id is not None and db.get(Meal, body.meal_id) is None:
        raise HTTPException(404, "meal not found")
    if entry is None:
        entry = MealPlanEntry(date=body.date, slot=body.slot)
        db.add(entry)
    entry.meal_id = body.meal_id
    entry.custom_text = body.custom_text
    db.commit()
    bus.publish("meals")
    return {"date": body.date.isoformat(), "slot": body.slot}


@router.post("/plan/grocery")
def generate_grocery(
    start: date_type = Query(...), end: date_type = Query(...), db: Session = Depends(get_db)
) -> dict:
    """Add every planned meal's ingredients to the grocery list (deduped)."""
    entries = (
        db.query(MealPlanEntry)
        .options(joinedload(MealPlanEntry.meal).joinedload(Meal.ingredients))
        .filter(MealPlanEntry.date >= start, MealPlanEntry.date <= end)
        .all()
    )
    grocery = db.query(ListModel).filter(ListModel.kind == "grocery").first()
    if grocery is None:
        grocery = ListModel(name="Groceries", kind="grocery", sort_order=0)
        db.add(grocery)
        db.flush()

    existing = {
        item.text.strip().lower()
        for item in db.query(ListItem).filter(ListItem.list_id == grocery.id).all()
    }
    added = 0
    for entry in entries:
        if not entry.meal:
            continue
        for ing in entry.meal.ingredients:
            key = ing.text.strip().lower()
            if key and key not in existing:
                db.add(ListItem(list_id=grocery.id, text=ing.text.strip(), sort_order=999))
                existing.add(key)
                added += 1
    db.commit()
    bus.publish("lists")
    return {"added": added, "list_id": grocery.id}
