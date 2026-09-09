#!/usr/bin/env bash
# Nightly backup of the local capitolscope Postgres to the hermes ZFS pool.
# Installed via cron (see crontab). Keeps 14 days of custom-format dumps.
set -euo pipefail
DEST=/mnt/hermes/backups/capitolscope
mkdir -p "$DEST"
TS=$(date +%F_%H%M)
OUT="$DEST/capitolscope-$TS.dump"
docker exec capitolscope-postgres pg_dump -U capitolscope -d capitolscope \
  --no-owner --no-privileges -Fc > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
# prune dumps older than 14 days
find "$DEST" -name 'capitolscope-*.dump' -mtime +14 -delete
echo "$(date -Is) backup ok: $OUT ($(du -h "$OUT" | cut -f1))"
