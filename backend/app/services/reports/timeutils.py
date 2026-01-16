from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

try:
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_rfc3339(s: str) -> datetime:
    """Parse RFC3339-like string into aware datetime. Supports trailing 'Z'."""
    if not isinstance(s, str) or not s:
        raise ValueError("Invalid RFC3339 string")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # treat naive as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fmt_rfc3339_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    s = dt.isoformat()
    return s[:-6] + "Z" if s.endswith("+00:00") else s


def fmt_rfc3339_local(dt: datetime, tz: str = "Asia/Kolkata") -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if ZoneInfo is not None:
        try:
            dt_local = dt.astimezone(ZoneInfo(tz))
        except Exception:
            if tz == "Asia/Kolkata":
                dt_local = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
            else:
                dt_local = dt.astimezone(timezone.utc)
    else:
        if tz == "Asia/Kolkata":
            dt_local = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        else:
            dt_local = dt.astimezone(timezone.utc)
    return dt_local.isoformat()


def _month_start_local(now_local: datetime) -> datetime:
    return now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _prev_month_start_local(now_local: datetime) -> datetime:
    first = _month_start_local(now_local)
    # go one day back to get previous month, then take its start
    prev_day = first - timedelta(days=1)
    return _month_start_local(prev_day)


def compute_range(
    preset: str,
    now_utc: Optional[datetime] = None,
    *,
    from_iso: Optional[str] = None,
    to_iso: Optional[str] = None,
    tz: str = "Asia/Kolkata",
) -> Tuple[datetime, datetime]:
    """
    Compute inclusive [from_utc, to_utc] time range for a given preset.
    Returns timezone-aware UTC datetimes.
    """
    p = (preset or "last24h").lower()
    now = (now_utc or _now_utc()).astimezone(timezone.utc)

    if p == "custom":
        if not from_iso or not to_iso:
            raise ValueError("custom preset requires from and to")
        f = _parse_rfc3339(from_iso)
        t = _parse_rfc3339(to_iso)
        if f > t:
            raise ValueError("from must be <= to")
        return f, t

    if p in ("last24h", "last7d", "last30d"):
        days = 1 if p == "last24h" else (7 if p == "last7d" else 30)
        return now - timedelta(days=days), now

    if p in ("this_month", "last_month"):
        if ZoneInfo is not None:
            try:
                z = ZoneInfo(tz)
                now_local = now.astimezone(z)
            except Exception:
                z = timezone(timedelta(hours=5, minutes=30)) if tz == "Asia/Kolkata" else timezone.utc
                now_local = now.astimezone(z)
        else:
            z = timezone(timedelta(hours=5, minutes=30)) if tz == "Asia/Kolkata" else timezone.utc
            now_local = now.astimezone(z)
        if p == "this_month":
            start_local = _month_start_local(now_local)
            start_utc = start_local.astimezone(timezone.utc)
            return start_utc, now
        else:
            this_start_local = _month_start_local(now_local)
            last_start_local = _prev_month_start_local(now_local)
            # end is start of this month (inclusive window uses <= end)
            start_utc = last_start_local.astimezone(timezone.utc)
            end_utc = this_start_local.astimezone(timezone.utc)
            return start_utc, end_utc

    # default
    return now - timedelta(days=1), now
