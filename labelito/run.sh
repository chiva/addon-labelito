#!/usr/bin/env bash
# Add-on entrypoint. addon_init.py translates /data/options.json into labelito's environment
# (and talks to the Supervisor: port-exposure guard + discovery announcement); this shell
# then seeds the user template directory and hands off to uvicorn.
set -euo pipefail

python3 /addon_init.py

set -a
# shellcheck disable=SC1091
source /tmp/labelito.env
set +a

# First boot: seed /config/templates with the bundled examples so the template picker isn't
# empty. Only when the directory is empty — user edits are never overwritten.
mkdir -p /config/templates
if [ -z "$(ls -A /config/templates)" ]; then
  cp /app/templates/*.yaml /config/templates/
  echo "[labelito-addon] seeded /config/templates with the bundled example templates"
fi

# Additive user overlays: custom TTF fonts and icons dropped into these folders are picked up
# alongside labelito's bundled fonts/icon collections. Created empty — no seeding needed.
mkdir -p /config/fonts /config/icons

# Single worker is intentional (in-process print lock + SQLite dedup) — see the upstream image.
exec uvicorn app.main:app --host 0.0.0.0 --port 8765 --log-level "${LOG_LEVEL:-info}"
