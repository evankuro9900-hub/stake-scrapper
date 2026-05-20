"""Parse GraphQL responses dari Stake.com ke struktur Python yg simple."""
from __future__ import annotations

from typing import Any


def has_live_stream(fixture: dict[str, Any]) -> bool:
    return bool(
        (fixture.get("betradarStream") or {}).get("exists")
        or (fixture.get("imgArenaStream") or {}).get("exists")
        or (fixture.get("abiosStream") or {}).get("exists")
        or (fixture.get("geniussportsStream") or {}).get("exists")
        or (fixture.get("statsPerformStream") or {}).get("isAvailable")
        or ((fixture.get("liveStream") or {}).get("data") or {}).get("isAvailable")
    )


def summarize_event_status(es: dict[str, Any] | None) -> dict[str, Any] | None:
    if not es:
        return None
    return {
        "__typename": es.get("__typename"),
        "match_status": es.get("matchStatus"),
        "home_score": es.get("homeScore"),
        "away_score": es.get("awayScore"),
        "clock": es.get("clock"),
        "period_scores": es.get("periodScores"),
        "statistic": es.get("statistic"),
    }


def _extract_1x2_odds(groups: list[dict[str, Any]]) -> dict[str, float | None]:
    """Find 1x2 market di group=winner, return odds by extId."""
    out: dict[str, float | None] = {"home": None, "draw": None, "away": None}
    for grp in groups or []:
        for tmpl in grp.get("templates", []) or []:
            for mkt in tmpl.get("markets", []) or []:
                if mkt.get("extId") != "1":
                    continue
                for o in mkt.get("outcomes", []) or []:
                    ext = o.get("extId")
                    if ext == "1":
                        out["home"] = o.get("odds")
                    elif ext == "2":
                        out["draw"] = o.get("odds")
                    elif ext == "3":
                        out["away"] = o.get("odds")
    return out


def parse_fixtures(
    sport_index_json: dict[str, Any],
    target_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Parse SportIndex response -> list dict fixture.

    target_keys = set('country_lower|slug_lower') untuk filter, atau None untuk semua.
    """
    slug_sport = (sport_index_json.get("data") or {}).get("slugSport")
    if not slug_sport:
        return []

    fixtures: list[dict[str, Any]] = []
    for category in slug_sport.get("categoryList") or []:
        country = category.get("name") or ""
        country_code = category.get("countryCode")
        for tournament in category.get("tournamentList") or []:
            slug = tournament.get("slug") or ""
            if target_keys is not None:
                key = f"{country.lower()}|{slug.lower()}"
                if key not in target_keys:
                    continue
            for fix in tournament.get("fixtureList") or []:
                if fix.get("status") != "active":
                    continue
                data = fix.get("data") or {}
                is_match = data.get("__typename") == "SportFixtureDataMatch"
                teams = data.get("teams") or []
                home = next(
                    (t.get("name") for t in teams if t.get("qualifier") == "home"), None
                )
                away = next(
                    (t.get("name") for t in teams if t.get("qualifier") == "away"), None
                )
                odds_1x2 = _extract_1x2_odds(fix.get("groups") or [])

                fixtures.append(
                    {
                        "stake_id": fix.get("id"),
                        "slug": fix.get("slug"),
                        "ext_id": fix.get("extId"),
                        "name": fix.get("name"),
                        "status": fix.get("status"),
                        "provider": fix.get("provider"),
                        "type": data.get("__typename"),
                        "start_time": data.get("startTime") if is_match else None,
                        "home_team": home,
                        "away_team": away,
                        "competitors": data.get("competitors") if is_match else [],
                        "tv_channels": data.get("tvChannels") if is_match else [],
                        "league_country": country,
                        "league_country_code": country_code,
                        "league_slug": slug,
                        "league_name": tournament.get("name"),
                        "league_id_stake": tournament.get("id"),
                        "market_count": fix.get("marketCount"),
                        "sgm_available": fix.get("sgmAvailable"),
                        "has_live_stream": has_live_stream(fix),
                        "live_widget_url": fix.get("liveWidgetUrl"),
                        "widget_url": fix.get("widgetUrl"),
                        "event_status": summarize_event_status(fix.get("eventStatus")),
                        "odds_home": odds_1x2["home"],
                        "odds_draw": odds_1x2["draw"],
                        "odds_away": odds_1x2["away"],
                    }
                )
    return fixtures


def parse_fixture_detail(detail_json: dict[str, Any]) -> dict[str, Any] | None:
    """Parse FixturePage_SlugFixture -> dict dengan markets di-flatten."""
    fixture = (detail_json.get("data") or {}).get("slugFixture")
    if not fixture:
        return None

    # Query produksi alias `groups(groups: $groups)` -> `group` (singular).
    # `groups` = list nama group semua (untuk navigation tab).
    filtered_groups = fixture.get("group") or []
    if not filtered_groups:
        # Fallback untuk query lama
        raw_groups = fixture.get("groups") or []
        if raw_groups and raw_groups[0].get("templates") is not None:
            filtered_groups = raw_groups

    data = fixture.get("data") or {}
    is_match = data.get("__typename") == "SportFixtureDataMatch"

    markets_by_group: dict[str, list[dict[str, Any]]] = {}
    for grp in filtered_groups:
        gname = grp.get("name") or "?"
        markets_by_group.setdefault(gname, [])
        for tmpl in grp.get("templates") or []:
            for mkt in tmpl.get("markets") or []:
                markets_by_group[gname].append(
                    {
                        "market_id": mkt.get("id"),
                        "market_name": mkt.get("name"),
                        "market_ext_id": mkt.get("extId"),
                        "specifiers": mkt.get("specifiers"),
                        "status": mkt.get("status"),
                        "provider": mkt.get("provider"),
                        "custom_bet_available": mkt.get("customBetAvailable"),
                        "template_name": tmpl.get("name"),
                        "template_ext_id": tmpl.get("extId"),
                        "outcomes": [
                            {
                                "id": o.get("id"),
                                "name": o.get("name"),
                                "odds": o.get("odds"),
                                "active": o.get("active"),
                                "ext_id": o.get("extId"),
                                "custom_bet_available": o.get("customBetAvailable"),
                            }
                            for o in (mkt.get("outcomes") or [])
                        ],
                    }
                )

    teams = data.get("teams") or []
    home = next((t.get("name") for t in teams if t.get("qualifier") == "home"), None)
    away = next((t.get("name") for t in teams if t.get("qualifier") == "away"), None)

    return {
        "stake_id": fixture.get("id"),
        "slug": fixture.get("slug"),
        "ext_id": fixture.get("extId"),
        "name": fixture.get("name"),
        "status": fixture.get("status"),
        "provider": fixture.get("provider"),
        "type": data.get("__typename"),
        "start_time": data.get("startTime") if is_match else None,
        "home_team": home,
        "away_team": away,
        "competitors": data.get("competitors") if is_match else [],
        "tv_channels": data.get("tvChannels") if is_match else [],
        "market_count": fixture.get("marketCount"),
        "custom_bet_available": fixture.get("customBetAvailable"),
        "sgm_available": fixture.get("sgmAvailable"),
        "has_live_stream": has_live_stream(fixture),
        "live_widget_url": fixture.get("liveWidgetUrl"),
        "widget_url": fixture.get("widgetUrl"),
        "event_status": summarize_event_status(fixture.get("eventStatus")),
        "available_groups": [
            {
                "name": g.get("name"),
                "translation": g.get("translation"),
                "rank": g.get("rank"),
            }
            for g in (fixture.get("groups") or [])
        ],
        "markets_by_group": markets_by_group,
    }


def extract_common_odds(detail: dict[str, Any]) -> dict[str, Any]:
    """Pull popular odds (1x2, O/U 2.5, BTTS, AH 0) for easy frontend display."""
    result: dict[str, Any] = {}
    markets = detail.get("markets_by_group") or {}

    main = markets.get("main") or []
    # 1x2
    for m in main:
        if m.get("market_ext_id") == "1":
            o = {o["ext_id"]: o["odds"] for o in m.get("outcomes", []) if o.get("odds") is not None}
            result["1x2"] = {
                "home": o.get("1"),
                "draw": o.get("2"),
                "away": o.get("3"),
            }
            break

    # O/U 2.5
    goals = markets.get("goals") or []
    for m in goals:
        if m.get("market_ext_id") == "18" and "total=2.5" in (m.get("specifiers") or ""):
            o = {x["ext_id"]: x["odds"] for x in m.get("outcomes", []) if x.get("odds") is not None}
            result["over_under_2.5"] = {"over": o.get("12"), "under": o.get("13")}
            break

    # BTTS
    for m in goals:
        if m.get("market_ext_id") == "29":
            o = {x["ext_id"]: x["odds"] for x in m.get("outcomes", []) if x.get("odds") is not None}
            result["btts"] = {"yes": o.get("74"), "no": o.get("76")}
            break

    # Asian Handicap 0
    asian = markets.get("AsianLines") or []
    for m in asian:
        if m.get("market_ext_id") == "16" and "hcp=0" in (m.get("specifiers") or ""):
            o = {x["ext_id"]: x["odds"] for x in m.get("outcomes", []) if x.get("odds") is not None}
            result["asian_handicap_0"] = {
                "home": o.get("1714"),
                "away": o.get("1715"),
            }
            break

    return result
