"""FastAPI app entry."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import TARGET_LEAGUES, settings
from .database import SessionFactory, init_models
from .models import ApiKey, League
from .routes import router
from .scraper import run_scrape
from .scrappey_pool import pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
)
log = logging.getLogger("app")

scheduler = AsyncIOScheduler()


async def _seed_initial_data() -> None:
    """Seed default leagues & initial Scrappey key (from env) on first start."""
    async with SessionFactory() as session:
        existing = await session.execute(select(League))
        existing_keys = {
            (lg.country.lower(), lg.slug.lower()) for lg in existing.scalars()
        }
        for tl in TARGET_LEAGUES:
            k = (tl["country"].lower(), tl["league_slug"].lower())
            if k not in existing_keys:
                session.add(
                    League(
                        country=tl["country"],
                        slug=tl["league_slug"],
                        label=tl["label"],
                    )
                )
        await session.commit()

        keys_res = await session.execute(select(ApiKey))
        if not keys_res.scalars().first():
            for env_key in settings.scrappey_initial_keys:
                if not env_key:
                    continue
                exists = await session.execute(
                    select(ApiKey).where(ApiKey.key == env_key)
                )
                if exists.scalar_one_or_none() is None:
                    session.add(ApiKey(key=env_key, label="initial"))
            await session.commit()


async def _scheduled_scrape() -> None:
    log.info("[SCHEDULER] auto scrape tick")
    try:
        await run_scrape(trigger="scheduled")
    except Exception:
        log.exception("scheduled scrape failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await _seed_initial_data()
    await pool.load_from_db()

    if settings.scrape_auto_start and settings.scrape_interval_minutes > 0:
        scheduler.add_job(
            _scheduled_scrape,
            "interval",
            minutes=settings.scrape_interval_minutes,
            id="auto_scrape",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        log.info(
            "Scheduler started — auto scrape tiap %d menit",
            settings.scrape_interval_minutes,
        )

    yield

    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    await pool.close()


app = FastAPI(title="Stake Scraper API", lifespan=lifespan)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# Serve frontend dari dist/ jika ada (single-app deployment).
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend_dist"
if _FRONTEND_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIR / "assets"), html=False),
        name="assets",
    )

    @app.get("/{path:path}", include_in_schema=False)
    async def _spa_fallback(path: str):  # type: ignore[unused-ignore]
        # Serve static files dari root (favicon, vite.svg, dll).
        candidate = _FRONTEND_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        # Default fallback ke index.html (SPA routes).
        return FileResponse(_FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": "Stake Scraper API",
            "docs": "/docs",
            "note": "Frontend dist tidak ditemukan — backend-only mode.",
        }
