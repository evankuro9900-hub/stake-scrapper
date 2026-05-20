"""FastAPI endpoints — RESTful interface to the scrape DB + scrape control."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_session
from .models import ApiKey, Fixture, League, Market, Outcome, ScrapeRun, utcnow
from .schemas import (
    ApiKeyCreate,
    ApiKeyOut,
    FixtureDetailOut,
    FixtureSummary,
    LeagueOut,
    MarketOut,
    OutcomeOut,
    ScrapeRunOut,
    StatsOut,
)
from .scraper import run_scrape, state
from .scrappey_pool import pool

router = APIRouter(prefix="/api")


def _api_key_to_out(k: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=k.id,
        label=k.label,
        key_preview=k.key_preview,
        is_active=k.is_active,
        dead_reason=k.dead_reason,
        request_count=k.request_count,
        last_used_at=k.last_used_at,
        last_dead_at=k.last_dead_at,
        created_at=k.created_at,
    )


# -------- API KEYS --------


@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys(session: AsyncSession = Depends(get_session)) -> list[ApiKeyOut]:
    result = await session.execute(select(ApiKey).order_by(ApiKey.id))
    return [_api_key_to_out(k) for k in result.scalars()]


@router.post("/api-keys", response_model=ApiKeyOut)
async def add_api_key(
    payload: ApiKeyCreate, session: AsyncSession = Depends(get_session)
) -> ApiKeyOut:
    key = payload.key.strip()
    if not key:
        raise HTTPException(400, "Key tidak boleh kosong")

    existing = await session.execute(select(ApiKey).where(ApiKey.key == key))
    db_key = existing.scalar_one_or_none()
    if db_key is None:
        db_key = ApiKey(key=key, label=payload.label, is_active=True)
        session.add(db_key)
    else:
        db_key.is_active = True
        db_key.dead_reason = None
        if payload.label:
            db_key.label = payload.label
    await session.commit()
    await session.refresh(db_key)
    # Refresh pool so it picks up the new key
    await pool.load_from_db()
    return _api_key_to_out(db_key)


@router.post("/api-keys/{key_id}/revive", response_model=ApiKeyOut)
async def revive_api_key(
    key_id: int, session: AsyncSession = Depends(get_session)
) -> ApiKeyOut:
    db_key = await session.get(ApiKey, key_id)
    if db_key is None:
        raise HTTPException(404, "Key tidak ditemukan")
    db_key.is_active = True
    db_key.dead_reason = None
    await session.commit()
    await session.refresh(db_key)
    await pool.load_from_db()
    return _api_key_to_out(db_key)


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    db_key = await session.get(ApiKey, key_id)
    if db_key is None:
        raise HTTPException(404, "Key tidak ditemukan")
    await session.delete(db_key)
    await session.commit()
    await pool.load_from_db()
    return {"ok": True}


# -------- LEAGUES --------


@router.get("/leagues", response_model=list[LeagueOut])
async def list_leagues(session: AsyncSession = Depends(get_session)) -> list[LeagueOut]:
    # Count fixtures per league
    counts = await session.execute(
        select(Fixture.league_id, func.count(Fixture.id)).group_by(Fixture.league_id)
    )
    count_map: dict[int, int] = {lid: c for lid, c in counts.all()}

    leagues = await session.execute(select(League).order_by(League.country, League.label))
    out: list[LeagueOut] = []
    for league in leagues.scalars():
        out.append(
            LeagueOut(
                id=league.id,
                country=league.country,
                slug=league.slug,
                label=league.label,
                sport=league.sport,
                enabled=league.enabled,
                fixture_count=count_map.get(league.id, 0),
                last_scraped_at=league.last_scraped_at,
            )
        )
    return out


# -------- FIXTURES --------


def _fixture_to_summary(f: Fixture, league: League | None) -> FixtureSummary:
    return FixtureSummary(
        id=f.id,
        slug=f.slug,
        stake_id=f.stake_id,
        name=f.name,
        home_team=f.home_team,
        away_team=f.away_team,
        start_time=f.start_time,
        status=f.status,
        market_count=f.market_count,
        has_live_stream=f.has_live_stream,
        sgm_available=f.sgm_available,
        odds_home=f.odds_home,
        odds_draw=f.odds_draw,
        odds_away=f.odds_away,
        league_id=f.league_id,
        league_label=league.label if league else None,
        league_country=league.country if league else None,
        league_slug=league.slug if league else None,
        league_sport=league.sport if league else None,
        detail_fetched_at=f.detail_fetched_at,
        updated_at=f.updated_at,
    )


@router.get("/fixtures", response_model=list[FixtureSummary])
async def list_fixtures(
    league_id: int | None = Query(None),
    league_slug: str | None = Query(None),
    status: str | None = Query(None),
    sport: str | None = Query(None),
    limit: int = Query(500, le=2000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[FixtureSummary]:
    stmt = (
        select(Fixture, League)
        .join(League, Fixture.league_id == League.id)
        .order_by(Fixture.start_time.asc().nulls_last(), Fixture.id.asc())
    )
    if league_id is not None:
        stmt = stmt.where(Fixture.league_id == league_id)
    if league_slug:
        stmt = stmt.where(League.slug == league_slug)
    if status:
        stmt = stmt.where(Fixture.status == status)
    if sport:
        stmt = stmt.where(League.sport == sport)
    stmt = stmt.limit(limit).offset(offset)

    rows = await session.execute(stmt)
    return [_fixture_to_summary(f, l) for f, l in rows.all()]


@router.get("/fixtures/{slug}", response_model=FixtureDetailOut)
async def fixture_detail(
    slug: str, session: AsyncSession = Depends(get_session)
) -> FixtureDetailOut:
    stmt = (
        select(Fixture)
        .where(Fixture.slug == slug)
        .options(
            selectinload(Fixture.league),
            selectinload(Fixture.markets).selectinload(Market.outcomes),
        )
    )
    res = await session.execute(stmt)
    fixture = res.scalar_one_or_none()
    if fixture is None:
        raise HTTPException(404, f"Fixture {slug} tidak ditemukan")

    markets_out: list[MarketOut] = []
    # Order: group, then template, then name
    for mkt in sorted(
        fixture.markets,
        key=lambda m: (m.group_name or "", m.template_ext_id or "", m.name),
    ):
        markets_out.append(
            MarketOut(
                name=mkt.name,
                ext_id=mkt.ext_id,
                group_name=mkt.group_name,
                template_name=mkt.template_name,
                specifiers=mkt.specifiers,
                status=mkt.status,
                provider=mkt.provider,
                outcomes=[
                    OutcomeOut(
                        name=o.name,
                        odds=o.odds,
                        ext_id=o.ext_id,
                        active=o.active,
                    )
                    for o in mkt.outcomes
                ],
            )
        )

    base = _fixture_to_summary(fixture, fixture.league)
    return FixtureDetailOut(
        **base.model_dump(),
        detailed_odds=fixture.detailed_odds,
        event_status=fixture.event_status,
        competitors=fixture.competitors,
        available_groups=fixture.available_groups,
        markets=markets_out,
    )


# -------- SCRAPE CONTROL --------


@router.post("/scrape/run")
async def trigger_scrape(
    limit: int | None = Query(None, ge=1, le=2000),
) -> dict[str, Any]:
    if state.running:
        return {"status": "already_running", **state.snapshot()}
    asyncio.create_task(run_scrape("manual", limit=limit))
    return {"status": "started", "limit": limit}


@router.get("/scrape/status")
async def scrape_status(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    snapshot = state.snapshot()
    res = await session.execute(
        select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(1)
    )
    last_run = res.scalar_one_or_none()
    return {
        "state": snapshot,
        "last_run": ScrapeRunOut.model_validate(last_run) if last_run else None,
        "pool": [
            {
                "key_preview": e.preview,
                "request_count": e.request_count,
                "dead": e.dead,
                "last_error": e.last_error,
            }
            for e in pool.entries
        ],
    }


@router.get("/scrape/runs", response_model=list[ScrapeRunOut])
async def list_scrape_runs(
    limit: int = Query(20, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[ScrapeRunOut]:
    res = await session.execute(
        select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(limit)
    )
    return [ScrapeRunOut.model_validate(r) for r in res.scalars()]


# -------- EXPORT --------


@router.get("/export/odds")
async def export_odds(
    league_id: int | None = Query(None),
    league_slug: str | None = Query(None),
    status: str | None = Query(None),
    sport: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Export semua data odds dalam format JSON lengkap."""
    from fastapi.responses import JSONResponse

    stmt = (
        select(Fixture, League)
        .join(League, Fixture.league_id == League.id)
        .options(
            selectinload(Fixture.markets).selectinload(Market.outcomes),
        )
        .order_by(Fixture.start_time.asc().nulls_last(), Fixture.id.asc())
    )
    if league_id is not None:
        stmt = stmt.where(Fixture.league_id == league_id)
    if league_slug:
        stmt = stmt.where(League.slug == league_slug)
    if status:
        stmt = stmt.where(Fixture.status == status)
    if sport:
        stmt = stmt.where(League.sport == sport)

    rows = await session.execute(stmt)

    export_data: list[dict[str, Any]] = []
    for fixture, league in rows.all():
        markets_data = []
        for mkt in sorted(
            fixture.markets,
            key=lambda m: (m.group_name or "", m.template_ext_id or "", m.name),
        ):
            markets_data.append(
                {
                    "name": mkt.name,
                    "ext_id": mkt.ext_id,
                    "group_name": mkt.group_name,
                    "template_name": mkt.template_name,
                    "specifiers": mkt.specifiers,
                    "status": mkt.status,
                    "provider": mkt.provider,
                    "outcomes": [
                        {
                            "name": o.name,
                            "odds": o.odds,
                            "ext_id": o.ext_id,
                            "active": o.active,
                        }
                        for o in mkt.outcomes
                    ],
                }
            )

        export_data.append(
            {
                "fixture": {
                    "id": fixture.id,
                    "slug": fixture.slug,
                    "stake_id": fixture.stake_id,
                    "name": fixture.name,
                    "home_team": fixture.home_team,
                    "away_team": fixture.away_team,
                    "start_time": fixture.start_time,
                    "status": fixture.status,
                    "market_count": fixture.market_count,
                    "has_live_stream": fixture.has_live_stream,
                    "sgm_available": fixture.sgm_available,
                    "detail_fetched_at": fixture.detail_fetched_at.isoformat() if fixture.detail_fetched_at else None,
                    "updated_at": fixture.updated_at.isoformat() if fixture.updated_at else None,
                },
                "league": {
                    "id": league.id,
                    "label": league.label,
                    "country": league.country,
                    "slug": league.slug,
                },
                "odds_1x2": {
                    "home": fixture.odds_home,
                    "draw": fixture.odds_draw,
                    "away": fixture.odds_away,
                },
                "detailed_odds": fixture.detailed_odds,
                "markets": markets_data,
                "competitors": fixture.competitors,
                "event_status": fixture.event_status,
            }
        )

    return JSONResponse(
        content={
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "total": len(export_data),
            "filters": {
                "league_id": league_id,
                "league_slug": league_slug,
                "status": status,
            },
            "data": export_data,
        },
        headers={
            "Content-Disposition": "attachment; filename=odds-export.json",
            "Content-Type": "application/json",
        },
    )


# -------- STATS --------


@router.get("/stats", response_model=StatsOut)
async def stats(session: AsyncSession = Depends(get_session)) -> StatsOut:
    fixtures_total = (await session.execute(select(func.count(Fixture.id)))).scalar() or 0
    with_details = (
        await session.execute(
            select(func.count(Fixture.id)).where(Fixture.detail_fetched_at.is_not(None))
        )
    ).scalar() or 0
    markets_total = (await session.execute(select(func.count(Market.id)))).scalar() or 0
    outcomes_total = (await session.execute(select(func.count(Outcome.id)))).scalar() or 0
    leagues_total = (await session.execute(select(func.count(League.id)))).scalar() or 0
    keys_active = (
        await session.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active.is_(True)))
    ).scalar() or 0
    keys_dead = (
        await session.execute(select(func.count(ApiKey.id)).where(ApiKey.is_active.is_(False)))
    ).scalar() or 0
    res = await session.execute(select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(1))
    last_run = res.scalar_one_or_none()
    return StatsOut(
        fixtures_total=fixtures_total,
        fixtures_with_details=with_details,
        markets_total=markets_total,
        outcomes_total=outcomes_total,
        leagues_total=leagues_total,
        api_keys_active=keys_active,
        api_keys_dead=keys_dead,
        last_run=ScrapeRunOut.model_validate(last_run) if last_run else None,
    )
