#!/usr/bin/env bash
set -euo pipefail

: "${CHROME_REAL_PATH:?CHROME_REAL_PATH must point to the installed Chrome binary}"
exec "$CHROME_REAL_PATH" --no-sandbox --disable-setuid-sandbox "$@"
