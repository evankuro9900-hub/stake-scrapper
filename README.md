# Stake Scraper — Deploy ke Fly.io

Bundle ini berisi backend FastAPI + frontend React (sudah di-build) yang
di-serve dari **satu** Fly app. Cukup deploy backend, frontend ikut otomatis.

## Yang sudah disiapkan

- `app/` — FastAPI backend (SQLAlchemy + APScheduler + Scrappey pool)
- `frontend_dist/` — Frontend React (sudah di-build, di-serve oleh backend dari `/`)
- `Dockerfile` — Multi-stage build (Poetry → slim runtime)
- `fly.toml` — Fly config dgn volume mount `/data` utk SQLite
- `deploy.sh` — Helper script yang otomatis bikin app + volume + secret + deploy

## Prasyarat

1. **Install `flyctl`** (sekali saja):
   ```bash
   curl -L https://fly.io/install.sh | sh
   export PATH="$HOME/.fly/bin:$PATH"
   ```
2. **Buat Fly personal access token**: https://fly.io/user/personal_access_tokens
3. **Punya Scrappey API key** (sudah kamu kasih: `vAhM9S9DnT6oNLQX0LtrSelNqQNaGFhd9ysQy3Yhx7dobUNAAIa9mgcGe813`)

## Deploy

```bash
cd stake-scraper-deploy
export FLY_API_TOKEN="<paste token kamu di sini>"
export SCRAPPEY_API_KEY="vAhM9S9DnT6oNLQX0LtrSelNqQNaGFhd9ysQy3Yhx7dobUNAAIa9mgcGe813"

# (Opsional) custom app name & region
# export FLY_APP_NAME="stake-scraper-evan"
# export FLY_REGION="sin"   # Singapore (default), atau "nrt"/"hkg"/"syd" dll

bash deploy.sh
```

Script-nya:
1. Bikin Fly app (kalau belum ada)
2. Tulis nama app ke `fly.toml`
3. Bikin volume 1GB di region kamu (utk SQLite persist)
4. Set `SCRAPPEY_API_KEY` + `SCRAPE_AUTO_START=true` + `SCRAPE_INTERVAL_MIN=10` jadi secret
5. Build Docker image + deploy

Output akhir bakal kasih URL: `https://<app-name>.fly.dev`

## Setelah deploy

Buka URL → lihat dashboard.

Trigger full scrape manual:
```bash
curl -X POST https://<app-name>.fly.dev/api/scrape/run
# atau dgn limit utk test cepat:
curl -X POST 'https://<app-name>.fly.dev/api/scrape/run?limit=5'
```

Cek status:
```bash
curl https://<app-name>.fly.dev/api/stats
curl https://<app-name>.fly.dev/api/scrape/status
```

## Catatan

- **Auto-refresh**: scheduler jalan tiap 10 menit (`SCRAPE_INTERVAL_MIN`). Matikan dgn set `SCRAPE_AUTO_START=false`.
- **Multi API key**: lewat Admin UI (`/admin` di frontend), atau pakai env var `SCRAPPEY_API_KEYS=key1,key2,key3` (comma-separated) saat deploy.
- **Cost estimate**: tiap fixture detail ~0.2 credit Scrappey (mode `request`). Full scrape 22 liga = 100-200 fixture/run = ~$0.05-0.10/run.
- **Volume**: data SQLite di `/data/app.db` persist antar deploy/restart. Hapus volume = reset data.

## Kalo kena error

```bash
# Lihat logs deploy
flyctl logs -a <app-name>

# SSH ke machine
flyctl ssh console -a <app-name>

# Redeploy kalo ada update
flyctl deploy -a <app-name>

# Hapus semua
flyctl apps destroy <app-name>
```
