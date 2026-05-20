"""ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(256), unique=True)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    dead_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_dead_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def key_preview(self) -> str:
        if len(self.key) <= 12:
            return self.key
        return f"{self.key[:6]}…{self.key[-4:]}"


class League(Base):
    __tablename__ = "leagues"
    __table_args__ = (UniqueConstraint("country", "slug", name="uq_country_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(64))
    slug: Mapped[str] = mapped_column(String(128))
    label: Mapped[str] = mapped_column(String(128))
    sport: Mapped[str] = mapped_column(String(32), default="soccer")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fixtures: Mapped[list["Fixture"]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True)
    stake_id: Mapped[str] = mapped_column(String(64), unique=True)
    slug: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    ext_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    home_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    away_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sgm_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_live_stream: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # cached basic odds (1x2)
    odds_home: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_draw: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_away: Mapped[float | None] = mapped_column(Float, nullable=True)

    # cached popular markets
    detailed_odds: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    event_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    competitors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    available_groups: Mapped[list | None] = mapped_column(JSON, nullable=True)

    detail_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    league: Mapped["League"] = relationship(back_populates="fixtures")
    markets: Mapped[list["Market"]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    stake_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(256))
    ext_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_ext_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    specifiers: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    custom_bet_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    fixture: Mapped["Fixture"] = relationship(back_populates="markets")
    outcomes: Mapped[list["Outcome"]] = relationship(
        back_populates="market", cascade="all, delete-orphan"
    )


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    stake_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(256))
    ext_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    custom_bet_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    market: Mapped["Market"] = relationship(back_populates="outcomes")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    trigger: Mapped[str] = mapped_column(String(32), default="manual")
    fixtures_scraped: Mapped[int] = mapped_column(Integer, default=0)
    fixtures_failed: Mapped[int] = mapped_column(Integer, default=0)
    estimated_credits: Mapped[float] = mapped_column(Float, default=0.0)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
