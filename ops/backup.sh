#!/bin/sh
# StockPilot database backups (runs inside the `backup` service; see docker-compose.yml).
#
#   backup.sh loop            run forever: back up every BACKUP_INTERVAL_HOURS (default 24)
#   backup.sh now             take one backup immediately
#   backup.sh list            list backups
#   backup.sh restore FILE    restore FILE (stop api + worker first!)
#
# Connection comes from the standard PG* environment variables.
set -eu

DIR=/backups
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
INTERVAL_HOURS="${BACKUP_INTERVAL_HOURS:-24}"
MIN_FREE_MB="${BACKUP_MIN_FREE_MB:-2048}"

log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S') [backup] $*"; }

free_mb() { df -Pm "$DIR" | awk 'NR==2 {print $4}'; }

backup_now() {
    free="$(free_mb)"
    if [ "$free" -lt "$MIN_FREE_MB" ]; then
        # Never risk filling the disk the database lives on.
        log "SKIPPED: only ${free} MB free (need ${MIN_FREE_MB} MB). Free up disk space."
        return 1
    fi
    file="$DIR/stockpilot-$(date -u +%Y%m%d-%H%M%S).dump"
    pg_dump --format=custom --no-owner --file="$file.partial"
    mv "$file.partial" "$file"
    log "OK: $(basename "$file") ($(du -h "$file" | cut -f1))"
    find "$DIR" -name 'stockpilot-*.dump' -type f -mtime "+$RETENTION_DAYS" -print -delete | sed 's/^/[backup] removed old /'
    rm -f "$DIR"/*.partial
}

case "${1:-now}" in
    loop)
        log "Starting: every ${INTERVAL_HOURS}h, keeping ${RETENTION_DAYS} days, in $DIR"
        until pg_isready -q; do sleep 2; done
        while true; do
            backup_now || log "Backup failed; will retry next cycle."
            sleep "$((INTERVAL_HOURS * 3600))"
        done
        ;;
    now)
        backup_now
        ;;
    list)
        ls -lh "$DIR"/stockpilot-*.dump 2>/dev/null || echo "No backups yet."
        ;;
    restore)
        file="${2:?usage: backup.sh restore stockpilot-YYYYmmdd-HHMMSS.dump}"
        case "$file" in /*) ;; *) file="$DIR/$file" ;; esac
        [ -f "$file" ] || { echo "Not found: $file"; exit 1; }
        log "Restoring $(basename "$file") into $PGDATABASE (existing objects are replaced)..."
        pg_restore --clean --if-exists --no-owner --single-transaction --dbname="$PGDATABASE" "$file"
        log "Restore complete. Start the api and worker again."
        ;;
    *)
        echo "usage: backup.sh loop|now|list|restore FILE"; exit 2
        ;;
esac
