"""ISO 8601 dates and periods for WARP (decision D19).

Dates, years and periods are kept in the data as ISO 8601 strings at whatever
granularity the source gave: "2023", "2024-05", "2026-03-31". This module
turns them into normalized bounds for comparison and export.

Why bounds and not strings: no string ordering handles "2024-05" against
"2023", and xsd:date, xsd:gYear and xsd:duration are not in the OWL 2 datatype
map, so they must never reach a generated file. Exporters write the verbatim
string plus the bounds as xsd:dateTime (with a Z timezone).

Bounds are half-open: ``lower`` is the first instant the value covers and
``upper`` is the first instant after it. "2024-05" covers
[2024-05-01T00:00:00Z, 2024-06-01T00:00:00Z). Two periods overlap when each
starts before the other ends. An open end (ongoing work) has upper bound None,
meaning unbounded.

Every later phase uses this module for period overlap; nothing compares date
strings directly.
"""

import calendar
import re
from datetime import datetime, timezone

ISO_PARTIAL = re.compile(r"^(\d{4})(?:-(0[1-9]|1[0-2])(?:-(0[1-9]|[12]\d|3[01]))?)?$")


class TimeError(ValueError):
    """A string is not an ISO 8601 year, year-month or date."""


def _dt(y, m=1, d=1):
    return datetime(y, m, d, tzinfo=timezone.utc)


def parse(value):
    """Return (year, month or None, day or None); raise TimeError if malformed."""
    if not isinstance(value, str):
        raise TimeError(f"not a string: {value!r}")
    m = ISO_PARTIAL.match(value.strip())
    if not m:
        raise TimeError(f"not an ISO 8601 year, year-month or date: {value!r}")
    y, mo, d = m.groups()
    y = int(y)
    mo = int(mo) if mo else None
    d = int(d) if d else None
    if d is not None and d > calendar.monthrange(y, mo)[1]:
        raise TimeError(f"no such day: {value!r}")
    return y, mo, d


def bounds(value):
    """Half-open [lower, upper) datetime bounds of an ISO 8601 partial date."""
    y, mo, d = parse(value)
    if mo is None:
        return _dt(y), _dt(y + 1)
    if d is None:
        return _dt(y, mo), (_dt(y + 1) if mo == 12 else _dt(y, mo + 1))
    lower = _dt(y, mo, d)
    last = calendar.monthrange(y, mo)[1]
    if d < last:
        upper = _dt(y, mo, d + 1)
    elif mo < 12:
        upper = _dt(y, mo + 1)
    else:
        upper = _dt(y + 1)
    return lower, upper


def period_bounds(start, end=None):
    """Bounds of a period from its start and (optional) end strings.

    The lower bound is the start of `start`; the upper bound is the end of
    `end`, or None when the period is open (ongoing). Raises TimeError when
    the end is before the start.
    """
    lower = bounds(start)[0]
    if end in (None, ""):
        return lower, None
    upper = bounds(end)[1]
    if upper <= lower:
        raise TimeError(f"period ends before it starts: {start!r} to {end!r}")
    return lower, upper


def overlaps(a, b):
    """True when two (lower, upper) bound pairs share any instant.

    An upper bound of None means open-ended (still running).
    """
    a_lo, a_hi = a
    b_lo, b_hi = b
    a_before_b_ends = b_hi is None or a_lo < b_hi
    b_before_a_ends = a_hi is None or b_lo < a_hi
    return a_before_b_ends and b_before_a_ends


def period_overlaps(p, q):
    """Overlap of two Period records (dicts with start and optional end)."""
    return overlaps(period_bounds(p["start"], p.get("end")),
                    period_bounds(q["start"], q.get("end")))


def xsd_datetime(dt):
    """Lexical form for an xsd:dateTime literal, always in UTC with Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
