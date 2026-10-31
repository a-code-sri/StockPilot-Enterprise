from datetime import date, datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware current UTC time. All persisted timestamps use this."""
    return datetime.now(timezone.utc)


def utctoday() -> date:
    """Current UTC date. Analytics buckets are UTC days, so ranges must use this too."""
    return utcnow().date()


def ensure_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC and convert aware ones to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_iso_datetime(raw) -> datetime | None:
    """Parse an ISO 8601 string (accepting a trailing 'Z'); returns an aware UTC datetime."""
    if isinstance(raw, datetime):
        return ensure_utc(raw)
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day, tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return ensure_utc(datetime.fromisoformat(s))
        except ValueError:
            return None
    return None
