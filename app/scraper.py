"""Scrape orchestrator — pull SportIndex + fixture details, simpan ke DB."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import TARGET_LEAGUES, settings
from .database import SessionFactory
from .models import Fixture, League, Market, Outcome, ScrapeRun, utcnow
from .parsers import extract_common_odds, parse_fixture_detail, parse_fixtures
from .scrappey_pool import pool
from .stake_queries import QUERY_FIXTURE_DETAIL, QUERY_SPORT_INDEX

log = logging.getLogger("scraper")

TARGET_LEAGUE_KEYS = {
    f"{tl['country'].lower()}|{tl['league_slug'].lower()}" for tl in TARGET_LEAGUES
}

# Sport slugs yang perlu di-fetch (deduplicated)
TARGET_SPORTS = list(dict.fromkeys(tl.get("sport", "soccer") for tl in TARGET_LEAGUES))


def _custom_headers(operation_name: str) -> dict[str, str]:
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "x-language": "en",
        "x-operation-name": operation_name,
        "x-operation-type": "query",
        "origin": "https://stake.com",
        "referer": "https://stake.com/sports/soccer",
    }
    if settings.stake_session_token:
        headers["x-access-token"] = settings.stake_session_token
        headers["cookie"] = f"session={settings.stake_session_token}"
    return headers


_HTML_WRAPPER_RE = re.compile(
    r'<div id="resultContainer"><div>(?P<body>.*?)</div></div>',
    re.DOTALL,
)


def _unwrap_response(raw: Any) -> dict[str, Any] | None:
    """Scrappey kadang wrap response body dalam HTML <div id="resultContainer">.

    Extract JSON dari wrapper kalau ada, otherwise parse raw langsung.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if text.startswith("<"):
        m = _HTML_WRAPPER_RE.search(text)
        if m:
            text = m.group("body").strip()
            # Scrappey kadang HTML-escape karakter dalam wrapper
            text = text.replace("&quot;", '"').replace("&amp;", "&")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def _stake_request(
    operation_name: str, query: str, variables: dict[str, Any]
) -> dict[str, Any] | None:
    """Send GraphQL request to stake.com via Scrappey pool."""
    post_data = json.dumps({"query": query, "variables": variables})
    solution = await pool.post(
        url=settings.stake_endpoint,
        post_data=post_data,
        custom_headers=_custom_headers(operation_name),
    )
    if solution is None:
        return None

    parsed = _unwrap_response(solution.get("response"))
    if parsed is None:
        snippet = str(solution.get("response", ""))[:200]
        log.error("Response tidak bisa di-parse utk %s: %s", operation_name, snippet)
        return None

    if parsed.get("errors"):
        log.error("GraphQL error utk %s: %s", operation_name, parsed["errors"])
        return None

    return parsed


async def fetch_sport_index(sport: str = "soccer") -> list[dict[str, Any]]:
    json_resp = await _stake_request(
        "SportIndex",
        QUERY_SPORT_INDEX,
        {"sport": sport, "group": "winner", "type": "popular"},
    )
    if not json_resp:
        return []
    fixtures = parse_fixtures(json_resp, target_keys=TARGET_LEAGUE_KEYS)
    # Tag each fixture with the sport it came from
    for f in fixtures:
        f["sport"] = sport
    return fixtures


async def fetch_fixture_detail(fixture_slug: str) -> dict[str, Any] | None:
    json_resp = await _stake_request(
        "FixturePage_SlugFixture",
        QUERY_FIXTURE_DETAIL,
        {
            "fixture": fixture_slug,
            "groups": list(settings.detail_groups),
        },
    )
    if not json_resp:
        return None
    return parse_fixture_detail(json_resp)


async def seed_leagues(session: AsyncSession) -> dict[tuple[str, str], int]:
    """Pastikan semua TARGET_LEAGUES ada di DB. Return mapping (country,slug)->id."""
    existing = await session.execute(select(League))
    mapping: dict[tuple[str, str], int] = {}
    for league in existing.scalars():
        mapping[(league.country.lower(), league.slug.lower())] = league.id

    for tl in TARGET_LEAGUES:
        key = (tl["country"].lower(), tl["league_slug"].lower())
        if key not in mapping:
            new_league = League(
                country=tl["country"],
                slug=tl["league_slug"],
                label=tl["label"],
                sport=tl.get("sport", "soccer"),
            )
            session.add(new_league)
            await session.flush()
            mapping[key] = new_league.id
        else:
            # Update sport field kalau belum di-set
            res = await session.execute(
                select(League).where(
                    League.country == tl["country"],
                    League.slug == tl["league_slug"],
                )
            )
            existing_league = res.scalar_one_or_none()
            if existing_league and existing_league.sport != tl.get("sport", "soccer"):
                existing_league.sport = tl.get("sport", "soccer")
    await session.commit()
    return mapping


async def _upsert_fixture(
    session: AsyncSession, fixture_data: dict[str, Any], league_id: int
) -> Fixture:
    stake_id = fixture_data["stake_id"]
    result = await session.execute(
        select(Fixture).where(Fixture.stake_id == stake_id)
    )
    fixture = result.scalar_one_or_none()
    if fixture is None:
        fixture = Fixture(stake_id=stake_id)
        session.add(fixture)

    fixture.slug = fixture_data.get("slug")
    fixture.ext_id = fixture_data.get("ext_id")
    fixture.league_id = league_id
    fixture.name = fixture_data.get("name") or ""
    fixture.home_team = fixture_data.get("home_team")
    fixture.away_team = fixture_data.get("away_team")
    fixture.start_time = fixture_data.get("start_time")
    fixture.status = fixture_data.get("status")
    fixture.provider = fixture_data.get("provider")
    fixture.market_count = fixture_data.get("market_count")
    fixture.sgm_available = fixture_data.get("sgm_available")
    fixture.has_live_stream = fixture_data.get("has_live_stream")
    fixture.type = fixture_data.get("type")
    fixture.odds_home = fixture_data.get("odds_home")
    fixture.odds_draw = fixture_data.get("odds_draw")
    fixture.odds_away = fixture_data.get("odds_away")
    fixture.event_status = fixture_data.get("event_status")
    fixture.competitors = fixture_data.get("competitors")
    fixture.updated_at = utcnow()
    await session.flush()
    return fixture


async def _save_fixture_detail(
    session: AsyncSession, fixture: Fixture, detail: dict[str, Any]
) -> None:
    fixture.market_count = detail.get("market_count")
    fixture.sgm_available = detail.get("sgm_available")
    fixture.has_live_stream = detail.get("has_live_stream")
    fixture.event_status = detail.get("event_status")
    fixture.competitors = detail.get("competitors")
    fixture.available_groups = detail.get("available_groups")
    fixture.detail_fetched_at = utcnow()
    fixture.detailed_odds = extract_common_odds(detail)

    # Wipe old markets to keep DB consistent
    await session.execute(
        delete(Market).where(Market.fixture_id == fixture.id)
    )

    for group_name, markets in (detail.get("markets_by_group") or {}).items():
        for mkt in markets:
            db_market = Market(
                fixture_id=fixture.id,
                stake_id=mkt.get("market_id") or "",
                name=mkt.get("market_name") or "",
                ext_id=mkt.get("market_ext_id"),
                group_name=group_name,
                template_name=mkt.get("template_name"),
                template_ext_id=mkt.get("template_ext_id"),
                specifiers=mkt.get("specifiers"),
                status=mkt.get("status"),
                provider=mkt.get("provider"),
                custom_bet_available=mkt.get("custom_bet_available"),
            )
            session.add(db_market)
            await session.flush()
            for o in mkt.get("outcomes") or []:
                session.add(
                    Outcome(
                        market_id=db_market.id,
                        stake_id=o.get("id") or "",
                        name=o.get("name") or "",
                        ext_id=o.get("ext_id"),
                        odds=o.get("odds"),
                        active=o.get("active"),
                        custom_bet_available=o.get("custom_bet_available"),
                    )
                )

    await session.flush()


class ScrapeState:
    """Tracks current run for logs / SSE / polling."""

    def __init__(self) -> None:
        self.run_id: int | None = None
        self.running: bool = False
        self.total: int = 0
        self.done: int = 0
        self.failed: int = 0
        self.last_message: str = ""

    def snapshot(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "running": self.running,
            "total": self.total,
            "done": self.done,
            "failed": self.failed,
            "last_message": self.last_message,
        }


state = ScrapeState()
_lock = asyncio.Lock()


async def run_scrape(trigger: str = "manual", limit: int | None = None) -> dict[str, Any]:
    """End-to-end scrape: SportIndex + detail untuk semua match di TARGET_LEAGUES.

    limit: kalau di-set, cuma scrape sejumlah fixture (untuk testing).
    """
    if state.running:
        return {"status": "already_running", **state.snapshot()}

    async with _lock:
        state.running = True
        state.done = 0
        state.failed = 0
        state.total = 0
        state.last_message = "Start: fetching SportIndex…"

        async with SessionFactory() as session:
            run = ScrapeRun(trigger=trigger)
            session.add(run)
            await session.commit()
            run_id = run.id
            state.run_id = run_id

        # Reload pool dari DB (kalau ada key baru yang ditambahin)
        await pool.load_from_db()

        try:
            fixtures_data: list[dict[str, Any]] = []
            for sport in TARGET_SPORTS:
                state.last_message = f"Fetching SportIndex: {sport}…"
                sport_fixtures = await fetch_sport_index(sport)
                fixtures_data.extend(sport_fixtures)
            if limit is not None and limit > 0:
                fixtures_data = fixtures_data[:limit]
            state.total = len(fixtures_data)
            state.last_message = f"Got {state.total} fixtures dari target leagues"
            log.info(state.last_message)

            async with SessionFactory() as session:
                league_map = await seed_leagues(session)

            for idx, fix_data in enumerate(fixtures_data, start=1):
                country = (fix_data.get("league_country") or "").lower()
                slug = (fix_data.get("league_slug") or "").lower()
                league_id = league_map.get((country, slug))
                if league_id is None:
                    continue

                async with SessionFactory() as session:
                    fixture = await _upsert_fixture(session, fix_data, league_id)
                    fixture_db_id = fixture.id
                    fixture_slug = fixture.slug
                    await session.commit()

                if not fixture_slug:
                    continue

                # Pacing
                await asyncio.sleep(settings.request_delay_ms / 1000)

                detail = await fetch_fixture_detail(fixture_slug)
                if not detail:
                    state.failed += 1
                    state.last_message = f"FAIL [{idx}/{state.total}] {fix_data.get('name')}"
                    log.warning(state.last_message)
                    if pool.count_alive() == 0:
                        state.last_message = "All keys dead, stop early"
                        log.error(state.last_message)
                        break
                    continue

                async with SessionFactory() as session:
                    fix_obj = await session.get(Fixture, fixture_db_id)
                    if fix_obj is None:
                        continue
                    await _save_fixture_detail(session, fix_obj, detail)
                    await session.commit()

                state.done += 1
                state.last_message = (
                    f"OK [{idx}/{state.total}] {fix_data.get('name')}"
                )
                log.info(state.last_message)

            # Persist key request counters
            await pool.persist_stats()

            credit_per_req = 0.2 if settings.scrappey_request_type == "request" else 1.2
            est_credit = (1 + state.done + state.failed) * credit_per_req

            async with SessionFactory() as session:
                run = await session.get(ScrapeRun, run_id)
                if run is not None:
                    run.finished_at = utcnow()
                    run.status = "completed"
                    run.fixtures_scraped = state.done
                    run.fixtures_failed = state.failed
                    run.estimated_credits = est_credit
                    await session.commit()

            return {"status": "completed", **state.snapshot()}
        except Exception as e:
            log.exception("scrape error")
            async with SessionFactory() as session:
                run = await session.get(ScrapeRun, run_id)
                if run is not None:
                    run.finished_at = utcnow()
                    run.status = "error"
                    run.error = str(e)[:1000]
                    await session.commit()
            state.last_message = f"ERROR: {e}"
            return {"status": "error", "error": str(e), **state.snapshot()}
        finally:
            state.running = False
