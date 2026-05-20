#!/usr/bin/env bash
# Deploy Stake Scraper ke Railway.app
# Prerequisites:
#   1. railway CLI installed (npm install -g @railway/cli)
#   2. RAILWAY_TOKEN env var set (dari https://railway.com/account/tokens)
#   3. SCRAPPEY_API_KEY env var set (your Scrappey API key)
#
# Usage:
#   export RAILWAY_TOKEN="..."
#   export SCRAPPEY_API_KEY="..."
#   bash deploy-railway.sh

set -euo pipefail

if [[ -z "${RAILWAY_TOKEN:-}" ]]; then
    echo "ERROR: RAILWAY_TOKEN env var tidak di-set"
    echo "Buat token di: https://railway.com/account/tokens"
    exit 1
fi

if [[ -z "${SCRAPPEY_API_KEY:-}" ]]; then
    echo "ERROR: SCRAPPEY_API_KEY env var tidak di-set"
    exit 1
fi

export RAILWAY_TOKEN

echo "==> Login ke Railway..."
railway whoami

echo "==> Membuat project baru..."
railway init --name "stake-scraper"

echo "==> Set environment variables..."
railway variables --set "SCRAPPEY_API_KEY=$SCRAPPEY_API_KEY"
railway variables --set "SCRAPE_AUTO_START=true"
railway variables --set "SCRAPE_INTERVAL_MIN=10"

echo "==> Deploy..."
railway up --detach

echo ""
echo "==> DONE!"
echo "==> Dashboard: https://railway.com/dashboard"
echo "==> Lihat logs: railway logs"
echo "==> Lihat URL:  railway domain"
