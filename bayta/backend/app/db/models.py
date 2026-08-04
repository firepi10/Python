from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    # Deterministic constraint names — required for SQLite batch migrations.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    color: Mapped[str] = mapped_column(String(30), default="blue")
    avatar_path: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CaldavAccount(Base):
    __tablename__ = "caldav_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    apple_id: Mapped[str] = mapped_column(String(255))
    password_enc: Mapped[bytes] = mapped_column(LargeBinary)
    server_url: Mapped[str] = mapped_column(String(255), default="https://caldav.icloud.com")
    principal_url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok|auth_failed|error
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    calendars: Mapped[list["Calendar"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Calendar(Base):
    __tablename__ = "calendars"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("caldav_accounts.id", ondelete="CASCADE"))
    remote_url: Mapped[str] = mapped_column(String(512), unique=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Calendar")
    color: Mapped[str | None] = mapped_column(String(30))
    ctag: Mapped[str | None] = mapped_column(String(255))
    sync_token: Mapped[str | None] = mapped_column(String(512))
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)

    account: Mapped[CaldavAccount] = relationship(back_populates="calendars")
    events: Mapped[list["Event"]] = relationship(
        back_populates="calendar", cascade="all, delete-orphan"
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("calendar_id", "uid", name="uq_events_calendar_uid"),
        CheckConstraint("origin IN ('remote','local')", name="ck_events_origin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    calendar_id: Mapped[int | None] = mapped_column(ForeignKey("calendars.id", ondelete="CASCADE"))
    uid: Mapped[str] = mapped_column(String(255))
    remote_href: Mapped[str | None] = mapped_column(String(512))
    etag: Mapped[str | None] = mapped_column(String(255))
    ics: Mapped[str] = mapped_column(Text)  # raw VCALENDAR — source of truth
    summary: Mapped[str] = mapped_column(String(512), default="")
    location: Mapped[str | None] = mapped_column(String(512))
    dtstart_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dtend_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    origin: Mapped[str] = mapped_column(String(10), default="local")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    # Direct person tag for locally created events; synced events inherit the
    # person from their calendar's profile mapping instead.
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))

    calendar: Mapped[Calendar | None] = relationship(back_populates="events")
    occurrences: Mapped[list["Occurrence"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Occurrence(Base):
    __tablename__ = "occurrences"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped[Event] = relationship(back_populates="occurrences")


class PendingOp(Base):
    __tablename__ = "pending_ops"
    __table_args__ = (
        CheckConstraint("op IN ('create','update','delete')", name="ck_pending_ops_op"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))
    op: Mapped[str] = mapped_column(String(10))
    payload_ics: Mapped[str | None] = mapped_column(Text)
    remote_href: Mapped[str | None] = mapped_column(String(512))
    etag: Mapped[str | None] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    original_path: Mapped[str] = mapped_column(String(512))
    display_path: Mapped[str] = mapped_column(String(512))
    thumb_path: Mapped[str] = mapped_column(String(512))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # upload | shared_album | icloudpd
    source: Mapped[str] = mapped_column(String(20), default="upload")
    source_guid: Mapped[str | None] = mapped_column(String(255), unique=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SharedAlbum(Base):
    __tablename__ = "shared_albums"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(120), unique=True)
    base_host: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    icon: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    recipe_url: Mapped[str | None] = mapped_column(String(512))
    tags: Mapped[str | None] = mapped_column(String(255))
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    ingredients: Mapped[list["MealIngredient"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan", order_by="MealIngredient.sort_order"
    )


class MealIngredient(Base):
    __tablename__ = "meal_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    meal: Mapped[Meal] = relationship(back_populates="ingredients")


class MealPlanEntry(Base):
    __tablename__ = "meal_plan"
    __table_args__ = (
        UniqueConstraint("date", "slot", name="uq_meal_plan_date_slot"),
        CheckConstraint("slot IN ('breakfast','lunch','dinner','snack')", name="ck_meal_plan_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[str] = mapped_column(String(12))
    meal_id: Mapped[int | None] = mapped_column(ForeignKey("meals.id", ondelete="SET NULL"))
    custom_text: Mapped[str | None] = mapped_column(String(255))

    meal: Mapped[Meal | None] = relationship()


class Chore(Base):
    __tablename__ = "chores"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    icon: Mapped[str | None] = mapped_column(String(40))
    # Deprecated single-person tag; assignment now lives in chore_assignees
    # (kept one version for updater rollback compatibility).
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    rrule: Mapped[str] = mapped_column(String(255), default="FREQ=DAILY")
    points: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    assignees: Mapped[list["ChoreAssignee"]] = relationship(
        back_populates="chore", cascade="all, delete-orphan"
    )


class ChoreAssignee(Base):
    """A chore can belong to several people (e.g. both kids); each person
    completes their own copy for the day."""

    __tablename__ = "chore_assignees"
    __table_args__ = (UniqueConstraint("chore_id", "profile_id", name="uq_chore_assignees"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey("chores.id", ondelete="CASCADE"))
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))

    chore: Mapped[Chore] = relationship(back_populates="assignees")


class ChoreCompletion(Base):
    __tablename__ = "chore_completions"
    __table_args__ = (
        UniqueConstraint(
            "chore_id", "due_date", "profile_id", name="uq_chore_completions_person"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey("chores.id", ondelete="CASCADE"))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    # who checked it off — NULL only for legacy/unassigned chores
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    points_awarded: Mapped[int] = mapped_column(Integer, default=1)


class Reward(Base):
    """A prize parents define; kids spend earned chore stars on it."""

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    icon: Mapped[str | None] = mapped_column(String(40))
    cost_points: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class RewardClaim(Base):
    __tablename__ = "reward_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id", ondelete="CASCADE"))
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    points_spent: Mapped[int] = mapped_column(Integer)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reward: Mapped[Reward] = relationship()


class ListModel(Base):
    __tablename__ = "lists"
    __table_args__ = (
        CheckConstraint("kind IN ('grocery','todo','custom')", name="ck_lists_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(12), default="custom")
    icon: Mapped[str | None] = mapped_column(String(40))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    items: Mapped[list["ListItem"]] = relationship(
        back_populates="list", cascade="all, delete-orphan", order_by="ListItem.sort_order"
    )


class ListItem(Base):
    __tablename__ = "list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(255))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    list: Mapped[ListModel] = relationship(back_populates="items")


class Countdown(Base):
    __tablename__ = "countdowns"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    target_date: Mapped[date] = mapped_column(Date)
    icon: Mapped[str | None] = mapped_column(String(40))
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id", ondelete="SET NULL"))


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON-encoded


class WeatherCache(Base):
    __tablename__ = "weather_cache"
    __table_args__ = (CheckConstraint("id = 1", name="ck_weather_cache_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    payload: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    detail: Mapped[str | None] = mapped_column(Text)
