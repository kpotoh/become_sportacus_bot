from __future__ import annotations

import re
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TIME_RANGE_RE = re.compile(
    r"^\s*(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})\s*$"
)
TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")


def parse_time_range(text: str) -> tuple[time, time] | None:
    m = TIME_RANGE_RE.match(text)
    if not m:
        return None
    h1, m1, h2, m2 = map(int, m.groups())
    if not (0 <= h1 <= 23 and 0 <= h2 <= 23 and 0 <= m1 <= 59 and 0 <= m2 <= 59):
        return None
    start, end = time(h1, m1), time(h2, m2)
    if start >= end:
        return None
    return start, end


def parse_time(text: str) -> time | None:
    m = TIME_RE.match(text)
    if not m:
        return None
    h, mi = map(int, m.groups())
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return time(h, mi)


def parse_positive_int(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    value = int(text)
    return value if value >= 1 else None


def validate_timezone(name: str) -> str | None:
    name = name.strip()
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        return None
    return name
