from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.events import bus
from app.db.models import ChoreCompletion, Profile, Reward, RewardClaim
from app.db.session import get_db

router = APIRouter(prefix="/rewards", tags=["rewards"])


class RewardIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    icon: str | None = None
    cost_points: int = Field(default=10, ge=1, le=10000)
    active: bool = True


def _reward_dict(r: Reward) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "icon": r.icon,
        "cost_points": r.cost_points,
        "active": r.active,
    }


def balances(db: Session) -> dict[int, dict]:
    """Per-person star ledger: lifetime earned minus spent."""
    earned = dict(
        db.query(ChoreCompletion.profile_id, func.sum(ChoreCompletion.points_awarded))
        .filter(ChoreCompletion.profile_id.isnot(None))
        .group_by(ChoreCompletion.profile_id)
        .all()
    )
    spent = dict(
        db.query(RewardClaim.profile_id, func.sum(RewardClaim.points_spent))
        .group_by(RewardClaim.profile_id)
        .all()
    )
    out = {}
    for profile in db.query(Profile).all():
        e = int(earned.get(profile.id) or 0)
        s = int(spent.get(profile.id) or 0)
        out[profile.id] = {"profile_id": profile.id, "earned": e, "spent": s, "balance": e - s}
    return out


@router.get("")
def list_rewards(db: Session = Depends(get_db)) -> dict:
    rewards = db.query(Reward).filter(Reward.active.is_(True)).order_by(Reward.cost_points).all()
    return {
        "rewards": [_reward_dict(r) for r in rewards],
        "balances": list(balances(db).values()),
    }


@router.post("", status_code=201)
def create_reward(body: RewardIn, db: Session = Depends(get_db)) -> dict:
    reward = Reward(**body.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    bus.publish("chores")
    return _reward_dict(reward)


@router.patch("/{reward_id}")
def update_reward(reward_id: int, body: RewardIn, db: Session = Depends(get_db)) -> dict:
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise HTTPException(404, "reward not found")
    for k, v in body.model_dump().items():
        setattr(reward, k, v)
    db.commit()
    bus.publish("chores")
    return _reward_dict(reward)


@router.delete("/{reward_id}", status_code=204)
def delete_reward(reward_id: int, db: Session = Depends(get_db)):
    reward = db.get(Reward, reward_id)
    if reward is None:
        raise HTTPException(404, "reward not found")
    db.delete(reward)
    db.commit()
    bus.publish("chores")


class ClaimIn(BaseModel):
    profile_id: int


@router.post("/{reward_id}/claim")
def claim_reward(reward_id: int, body: ClaimIn, db: Session = Depends(get_db)) -> dict:
    reward = db.get(Reward, reward_id)
    if reward is None or not reward.active:
        raise HTTPException(404, "reward not found")
    profile = db.get(Profile, body.profile_id)
    if profile is None:
        raise HTTPException(404, "person not found")
    balance = balances(db).get(body.profile_id, {}).get("balance", 0)
    if balance < reward.cost_points:
        raise HTTPException(
            422, f"{profile.name} needs {reward.cost_points - balance} more stars for that"
        )
    db.add(
        RewardClaim(
            reward_id=reward.id, profile_id=body.profile_id, points_spent=reward.cost_points
        )
    )
    db.commit()
    bus.publish("chores")
    return {
        "claimed": True,
        "reward": reward.title,
        "profile_id": body.profile_id,
        "balance": balance - reward.cost_points,
    }


@router.get("/claims")
def claim_history(limit: int = 20, db: Session = Depends(get_db)) -> list[dict]:
    claims = (
        db.query(RewardClaim)
        .options(joinedload(RewardClaim.reward))
        .order_by(RewardClaim.claimed_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        {
            "id": c.id,
            "reward": c.reward.title if c.reward else "?",
            "icon": c.reward.icon if c.reward else None,
            "profile_id": c.profile_id,
            "points_spent": c.points_spent,
            "claimed_at": c.claimed_at.isoformat(),
        }
        for c in claims
    ]
