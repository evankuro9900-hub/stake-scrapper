"""Aplikasi config — load env vars + constants."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no external dep). Looks at backend root."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv()


def _resolve_db_path() -> str:
    # Fly volume mounted di /data — kalau ada, pakai. Otherwise local sqlite.
    data_dir = Path("/data")
    if data_dir.is_dir() and os.access(data_dir, os.W_OK):
        return str(data_dir / "app.db")
    fallback = Path(__file__).resolve().parent.parent / "app.db"
    return str(fallback)


@dataclass
class Settings:
    db_path: str = _resolve_db_path()
    db_url: str = ""

    # Scrappey
    scrappey_base_url: str = "https://publisher.scrappey.com/api/v1"
    scrappey_request_type: str = os.environ.get("SCRAPPEY_MODE", "request")
    scrappey_initial_keys: tuple[str, ...] = tuple(
        k.strip()
        for k in (
            os.environ.get("SCRAPPEY_API_KEYS")
            or os.environ.get("SCRAPPEY_API_KEY")
            or os.environ.get("scrapey_api")
            or ""
        ).split(",")
        if k.strip()
    )

    # Stake
    stake_endpoint: str = "https://stake.com/_api/graphql"
    stake_session_token: str | None = os.environ.get("STAKE_SESSION_TOKEN") or None

    # Scrape behavior
    request_delay_ms: int = int(os.environ.get("REQUEST_DELAY", "1500"))
    max_retries: int = int(os.environ.get("MAX_RETRIES", "3"))
    retry_delay_ms: int = int(os.environ.get("RETRY_DELAY", "2000"))
    detail_groups: tuple[str, ...] = (
        "main",
        "goals",
        "AsianLines",
        "corners",
        "cards",
        "1st2ndhalfmarkets",
    )

    # Scheduler
    scrape_interval_minutes: int = int(os.environ.get("SCRAPE_INTERVAL_MIN", "10"))
    scrape_auto_start: bool = os.environ.get("SCRAPE_AUTO_START", "true").lower() == "true"

    def __post_init__(self) -> None:
        self.db_url = f"sqlite+aiosqlite:///{self.db_path}"


settings = Settings()


# Liga target — (sport, country yang tampil di stake categoryList.name, slug tournament,
# label untuk display di frontend)
TARGET_LEAGUES: list[dict[str, str]] = [
    # ── SOCCER ─────────────────────────────────────────────────────────────────
    # Eropa
    {"sport": "soccer", "country": "England",      "league_slug": "premier-league",            "label": "Premier League"},
    {"sport": "soccer", "country": "Spain",        "league_slug": "la-liga",                   "label": "La Liga"},
    {"sport": "soccer", "country": "Italy",        "league_slug": "serie-a",                   "label": "Serie A"},
    {"sport": "soccer", "country": "France",       "league_slug": "ligue-1",                   "label": "Ligue 1"},
    {"sport": "soccer", "country": "Netherlands",  "league_slug": "eredivisie",                "label": "Eredivisie"},
    {"sport": "soccer", "country": "Turkiye",      "league_slug": "super-lig",                 "label": "Süper Lig"},
    {"sport": "soccer", "country": "Scotland",     "league_slug": "premiership",               "label": "Scottish Premiership"},
    {"sport": "soccer", "country": "Belgium",      "league_slug": "first-division-a",          "label": "Belgian Pro League"},
    {"sport": "soccer", "country": "Poland",       "league_slug": "ekstraklasa",               "label": "Ekstraklasa"},
    # Amerika
    {"sport": "soccer", "country": "USA",          "league_slug": "major-league-soccer",       "label": "MLS"},
    {"sport": "soccer", "country": "Brazil",       "league_slug": "brasileiro-serie-a",        "label": "Brasileirão Série A"},
    {"sport": "soccer", "country": "Colombia",     "league_slug": "primera-a-apertura",        "label": "Colombia Primera A (Apertura)"},
    {"sport": "soccer", "country": "Colombia",     "league_slug": "primera-a-finalizacion",    "label": "Colombia Primera A (Finalización)"},
    {"sport": "soccer", "country": "Argentina",    "league_slug": "superliga",                 "label": "Argentine Primera División (LFP)"},
    {"sport": "soccer", "country": "Mexico",       "league_slug": "primera-division-clausura", "label": "Liga MX (Clausura)"},
    {"sport": "soccer", "country": "Mexico",       "league_slug": "primera-division-apertura", "label": "Liga MX (Apertura)"},
    {"sport": "soccer", "country": "Canada",       "league_slug": "canadian-premier-league",   "label": "Canadian Premier League"},
    # Asia
    {"sport": "soccer", "country": "Japan",        "league_slug": "j-league",                  "label": "J.League"},
    {"sport": "soccer", "country": "South Korea",  "league_slug": "k-league-1",                "label": "K League 1"},
    {"sport": "soccer", "country": "China",        "league_slug": "chinese-super-league",      "label": "Chinese Super League"},
    {"sport": "soccer", "country": "India",        "league_slug": "indian-super-league",       "label": "Indian Super League"},
    {"sport": "soccer", "country": "Indonesia",    "league_slug": "liga-1",                    "label": "Indonesia Liga 1"},
    {"sport": "soccer", "country": "Saudi Arabia", "league_slug": "saudi-prof-league",         "label": "Saudi Pro League"},
    {"sport": "soccer", "country": "Vietnam",      "league_slug": "v-league-1",                "label": "V.League 1"},
    # ── BASKETBALL ─────────────────────────────────────────────────────────────
    {"sport": "basketball", "country": "USA",      "league_slug": "nba",                       "label": "NBA"},
    {"sport": "basketball", "country": "USA",      "league_slug": "wnba",                      "label": "WNBA"},
]
