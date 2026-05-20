"""Pydantic response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApiKeyOut(_Base):
    id: int
    label: str | None
    key_preview: str
    is_active: bool
    dead_reason: str | None
    request_count: int
    last_used_at: datetime | None
    last_dead_at: datetime | None
    created_at: datetime


class ApiKeyCreate(BaseModel):
    key: str
    label: str | None = None


class LeagueOut(_Base):
    id: int
    country: str
    slug: str
    label: str
    sport: str = "soccer"
    enabled: bool
    fixture_count: int = 0
    last_scraped_at: datetime | None = None


class FixtureSummary(_Base):
    id: int
    slug: str
    stake_id: str
    name: str
    home_team: str | None
    away_team: str | None
    start_time: str | None
    status: str | None
    market_count: int | None
    has_live_stream: bool | None
    sgm_available: bool | None
    odds_home: float | None
    odds_draw: float | None
    odds_away: float | None
    league_id: int
    league_label: str | None = None
    league_country: str | None = None
    league_slug: str | None = None
    league_sport: str | None = None
    detail_fetched_at: datetime | None
    updated_at: datetime


class OutcomeOut(_Base):
    name: str
    odds: float | None
    ext_id: str | None
    active: bool | None


class MarketOut(_Base):
    name: str
    ext_id: str | None
    group_name: str | None
    template_name: str | None
    specifiers: str | None
    status: str | None
    provider: str | None
    outcomes: list[OutcomeOut]


class FixtureDetailOut(FixtureSummary):
    detailed_odds: dict[str, Any] | None
    event_status: dict[str, Any] | None
    competitors: list[Any] | None
    available_groups: list[Any] | None
    markets: list[MarketOut]


class ScrapeRunOut(_Base):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    trigger: str
    fixtures_scraped: int
    fixtures_failed: int
    estimated_credits: float
    error: str | None


class StatsOut(BaseModel):
    fixtures_total: int
    fixtures_with_details: int
    markets_total: int
    outcomes_total: int
    leagues_total: int
    api_keys_active: int
    api_keys_dead: int
    last_run: ScrapeRunOut | None
