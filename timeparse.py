"""Parse human reminder time expressions into an absolute UTC datetime.

Supported forms (case-insensitive):
  - "in 10 minutes", "in 2 hours", "in 1 day", "in 30 sec"
  - "at 18:30", "at 9am", "at 9:15 pm"  (today, or tomorrow if already past)
  - "tomorrow 08:00"

Returns a timezone-aware UTC datetime, or None if it can't parse.
The remaining message text (the reminder body) is returned separately.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config

_LOCAL_TZ = ZoneInfo(config.TIMEZONE)
_UTC = ZoneInfo("UTC")

_UNIT_SECONDS = {
    "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
    "day": 86400, "days": 86400,
}


def _now_local() -> datetime:
    return datetime.now(tz=_LOCAL_TZ)


def _parse_clock(text: str, base_day: datetime):
    """Parse an 'at HH:MM' / 'H am/pm' clock time onto base_day (local)."""
    m = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text, re.IGNORECASE
    )
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = (m.group(3) or "").lower()

    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:
        return None
    return base_day.replace(hour=hour, minute=minute, second=0, microsecond=0)


def parse(text: str):
    """Return (due_at_utc, reminder_body) or (None, None)."""
    raw = text.strip()
    lowered = raw.lower()

    # Relative: "in <n> <unit>"
    rel = re.search(
        r"\bin\s+(\d+)\s*(sec|secs|second|seconds|min|mins|minute|minutes|"
        r"hour|hours|hr|hrs|day|days)\b",
        lowered,
    )
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2)
        due_local = _now_local() + timedelta(seconds=amount * _UNIT_SECONDS[unit])
        body = (raw[: rel.start()] + raw[rel.end():]).strip(" ,-") or "Reminder"
        return due_local.astimezone(_UTC), body

    # "tomorrow [HH:MM]"
    if "tomorrow" in lowered:
        base = (_now_local() + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        clock = _parse_clock(lowered.replace("tomorrow", " "), base)
        due_local = clock or base
        body = re.sub(r"\btomorrow\b", "", raw, flags=re.IGNORECASE)
        body = re.sub(r"\bat\b", "", body, flags=re.IGNORECASE).strip(" ,-")
        return due_local.astimezone(_UTC), (body or "Reminder")

    # "at <clock>" today (or tomorrow if past)
    if re.search(r"\bat\b", lowered):
        clock = _parse_clock(lowered, _now_local())
        if clock:
            if clock <= _now_local():
                clock += timedelta(days=1)
            body = re.sub(
                r"\bat\b.*", "", raw, flags=re.IGNORECASE
            ).strip(" ,-") or "Reminder"
            return clock.astimezone(_UTC), body

    return None, None
