#!/usr/bin/env bash
# Deploy Stake Scraper backend to your Fly.io personal account.
# Prerequisites:
#   1. flyctl installed (https://fly.io/docs/flyctl/install/)
#   2. FLY_API_TOKEN env var set (from https://fly.io/user/personal_access_tokens)
#   3. SCRAPPEY_API_KEY env var set (your Scrappey API key)
#
# Usage:
#   export FLY_API_TOKEN="..."
#   export SCRAPPEY_API_KEY="vAhM9S9DnT6oNLQX0LtrSelNqQNaGFhd9ysQy3Yhx7dobUNAAIa9mgcGe813"
#   bash deploy.sh

set -euo pipefail

if [[ -z "${FLY_API_TOKEN:-}" ]]; then
    echo "ERROR: FLY_API_TOKEN env var not set"
    echo "Get one at https://fly.io/user/personal_access_tokens"
    exit 1
fi

if [[ -z "${SCRAPPEY_API_KEY:-}" ]]; then
    echo "ERROR: SCRAPPEY_API_KEY env var not set"
    echo "Get one at https://app.scrappey.com/#/"
    exit 1
fi

APP_NAME="${FLY_APP_NAME:-stake-scraper-$(openssl rand -hex 3 2>/dev/null || echo $$)}"
REGION="${FLY_REGION:-sin}"
VOLUME_NAME="${FLY_VOLUME_NAME:-stake_data}"

echo "==> App name: $APP_NAME"
echo "==> Region: $REGION"
echo "==> Volume: $VOLUME_NAME"
echo

export FLY_API_TOKEN

# 1. Create app
if ! flyctl apps list 2>/dev/null | grep -q "^${APP_NAME}\b"; then
    echo "==> Creating Fly app '$APP_NAME'..."
    flyctl apps create "$APP_NAME" --org personal
fi

# 2. Patch fly.toml with app name
TMP_TOML="$(mktemp)"
{
    echo "app = \"$APP_NAME\""
    cat fly.toml
} > "$TMP_TOML"
mv "$TMP_TOML" fly.toml

# 3. Create persistent volume (idempotent — skip if exists)
echo "==> Ensuring volume '$VOLUME_NAME' exists in $REGION..."
if ! flyctl volumes list -a "$APP_NAME" 2>/dev/null | grep -q "$VOLUME_NAME"; then
    flyctl volumes create "$VOLUME_NAME" \
        --region "$REGION" \
        --size 1 \
        --yes \
        -a "$APP_NAME"
fi

# 4. Set secrets
echo "==> Setting secrets..."
flyctl secrets set \
    SCRAPPEY_API_KEY="$SCRAPPEY_API_KEY" \
    SCRAPE_AUTO_START=true \
    SCRAPE_INTERVAL_MIN=10 \
    -a "$APP_NAME" \
    --stage

# 5. Deploy
echo "==> Deploying..."
flyctl deploy -a "$APP_NAME" --ha=false

echo
echo "==> DONE"
echo "==> URL: https://${APP_NAME}.fly.dev"
echo "==> Test: curl https://${APP_NAME}.fly.dev/healthz"
echo "==> Trigger scrape:"
echo "      curl -X POST https://${APP_NAME}.fly.dev/api/scrape/run"
