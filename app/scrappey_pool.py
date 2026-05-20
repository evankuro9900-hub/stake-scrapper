"""ScrappeyPool — manage multiple Scrappey API keys with auto-rotation.

Pool stores active session per key. Kalau satu key invalid / out of credit,
mark dead dan rotate ke key berikutnya. Designed sebagai singleton dalam process.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import SessionFactory
from .models import ApiKey, utcnow

log = logging.getLogger("scrappey")

KEY_EXHAUSTED_RE = re.compile(
    r"invalid api ?key|api ?key not found|insufficient credit|out of credit|"
    r"no credit|subscription expired|quota exceeded|expired|unauthorized|"
    r"status code 40[0-3]",
    re.IGNORECASE,
)


@dataclass
class KeyEntry:
    """In-memory tracking for one key during a run."""

    db_id: int
    key: str
    label: str
    session_id: str | None = None
    dead: bool = False
    request_count: int = 0
    last_error: str | None = None

    @property
    def preview(self) -> str:
        return f"{self.key[:6]}…{self.key[-4:]}" if len(self.key) > 12 else self.key


class ScrappeyPool:
    """Pool of Scrappey keys with auto-rotation on auth/credit errors."""

    def __init__(self) -> None:
        self.entries: list[KeyEntry] = []
        self.active_idx: int = 0
        self.client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    async def load_from_db(self) -> None:
        """Refresh pool from DB. Hanya pakai key yang is_active=True."""
        async with SessionFactory() as session:
            result = await session.execute(
                select(ApiKey).where(ApiKey.is_active.is_(True)).order_by(ApiKey.id)
            )
            keys = result.scalars().all()

        self.entries = [
            KeyEntry(db_id=k.id, key=k.key, label=k.label or k.key_preview)
            for k in keys
        ]
        self.active_idx = 0
        log.info("Pool loaded with %d active key(s)", len(self.entries))

    def _ensure_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=120.0)
        return self.client

    async def close(self) -> None:
        for entry in self.entries:
            if entry.session_id:
                try:
                    await self._destroy_session(entry)
                except Exception as e:
                    log.warning("destroy session failed: %s", e)
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    def active(self) -> KeyEntry | None:
        for offset in range(len(self.entries)):
            idx = (self.active_idx + offset) % len(self.entries)
            if not self.entries[idx].dead:
                self.active_idx = idx
                return self.entries[idx]
        return None

    def count_alive(self) -> int:
        return sum(1 for e in self.entries if not e.dead)

    async def mark_dead(self, entry: KeyEntry, reason: str) -> KeyEntry | None:
        entry.dead = True
        entry.last_error = reason[:240]
        log.warning("[POOL] key %s DEAD: %s", entry.preview, reason[:120])

        # Persist to DB
        async with SessionFactory() as session:
            db_key = await session.get(ApiKey, entry.db_id)
            if db_key is not None:
                db_key.is_active = False
                db_key.dead_reason = entry.last_error
                db_key.last_dead_at = utcnow()
                await session.commit()

        # Rotate
        for offset in range(1, len(self.entries) + 1):
            idx = (self.active_idx + offset) % len(self.entries)
            if not self.entries[idx].dead:
                self.active_idx = idx
                next_entry = self.entries[idx]
                log.warning("[POOL] -> rotate ke key %s", next_entry.preview)
                return next_entry
        return None

    async def _create_session(self, entry: KeyEntry) -> str:
        """Create Scrappey session for this key."""
        client = self._ensure_client()
        url = f"{settings.scrappey_base_url}?key={entry.key}"
        resp = await client.post(url, json={"cmd": "sessions.create"})
        resp.raise_for_status()
        data = resp.json()
        session_id = data.get("session")
        if not session_id:
            raise RuntimeError(f"sessions.create returned no session: {data}")
        entry.session_id = session_id
        log.info("[POOL] key %s -> session %s", entry.preview, session_id)
        return session_id

    async def _destroy_session(self, entry: KeyEntry) -> None:
        if not entry.session_id:
            return
        client = self._ensure_client()
        url = f"{settings.scrappey_base_url}?key={entry.key}"
        try:
            await client.post(
                url, json={"cmd": "sessions.destroy", "session": entry.session_id}
            )
        finally:
            entry.session_id = None

    async def ensure_session(self) -> tuple[KeyEntry, str]:
        """Get active key + its session, creating one if needed.

        Auto-rotate kalau createSession gagal (key invalid/expired).
        """
        async with self._lock:
            while True:
                entry = self.active()
                if entry is None:
                    raise RuntimeError("Tidak ada API key aktif di pool")
                if entry.session_id:
                    return entry, entry.session_id
                try:
                    session_id = await self._create_session(entry)
                    return entry, session_id
                except Exception as e:
                    msg = str(e)
                    next_entry = await self.mark_dead(entry, f"createSession: {msg}")
                    if next_entry is None:
                        raise RuntimeError(
                            "Semua API key dead saat createSession"
                        ) from e

    async def post(
        self,
        url: str,
        post_data: str,
        custom_headers: dict[str, str],
        max_retries: int | None = None,
    ) -> dict[str, Any] | None:
        """Send a request via Scrappey, with auto-retry + auto-rotate."""
        retries = max_retries if max_retries is not None else settings.max_retries

        attempt = 0
        while attempt < retries:
            attempt += 1

            entry, session_id = await self.ensure_session()
            client = self._ensure_client()
            scrappey_url = f"{settings.scrappey_base_url}?key={entry.key}"

            payload = {
                "cmd": f"{settings.scrappey_request_type}.post",
                "url": url,
                "session": session_id,
                "postData": post_data,
                "customHeaders": custom_headers,
            }

            try:
                resp = await client.post(scrappey_url, json=payload)
                data = resp.json()
            except Exception as e:
                msg = str(e)
                # Network/transport error -> retry with same key
                if attempt < retries:
                    log.warning("Scrappey transport error attempt %d: %s", attempt, msg)
                    await asyncio.sleep(settings.retry_delay_ms / 1000 * attempt)
                    continue
                log.error("Scrappey transport error giving up: %s", msg)
                return None

            entry.request_count += 1

            outcome = data.get("data")
            if outcome != "success":
                err_msg = data.get("error") or str(data)
                # Key exhausted -> rotate, jangan counted retry biasa
                if KEY_EXHAUSTED_RE.search(err_msg):
                    next_entry = await self.mark_dead(entry, err_msg)
                    if next_entry is None:
                        log.error("Semua key habis untuk %s", url)
                        return None
                    attempt -= 1
                    continue
                # CF transient -> retry
                if re.search(
                    r"cloudflare was not solved|cookies invalid|solve again",
                    err_msg,
                    re.IGNORECASE,
                ):
                    if attempt < retries:
                        log.warning(
                            "[RETRY %d/%d] CF transient: %s",
                            attempt,
                            retries,
                            err_msg[:80],
                        )
                        await asyncio.sleep(settings.retry_delay_ms / 1000 * attempt)
                        continue
                log.error("Scrappey error: %s", err_msg[:200])
                return None

            solution = data.get("solution") or {}
            return solution

        return None

    async def persist_stats(self) -> None:
        """Save request_count + last_used to DB."""
        if not self.entries:
            return
        now = utcnow()
        async with SessionFactory() as session:
            for entry in self.entries:
                db_key = await session.get(ApiKey, entry.db_id)
                if db_key is None:
                    continue
                db_key.request_count = (db_key.request_count or 0) + entry.request_count
                if entry.request_count > 0:
                    db_key.last_used_at = now
            await session.commit()
        for entry in self.entries:
            entry.request_count = 0


# Singleton instance
pool = ScrappeyPool()
