"""ISO 8601 bounds and period overlap (scripts/warp_time.py, decision D19)."""

from datetime import datetime, timezone

import pytest

import warp_time as wt


def dt(*a):
    return datetime(*a, tzinfo=timezone.utc)


@pytest.mark.parametrize("value, lower, upper", [
    ("2023", dt(2023, 1, 1), dt(2024, 1, 1)),
    ("2024-05", dt(2024, 5, 1), dt(2024, 6, 1)),
    ("2024-12", dt(2024, 12, 1), dt(2025, 1, 1)),
    ("2026-03-31", dt(2026, 3, 31), dt(2026, 4, 1)),
    ("2024-02-29", dt(2024, 2, 29), dt(2024, 3, 1)),
    ("2023-12-31", dt(2023, 12, 31), dt(2024, 1, 1)),
])
def test_bounds(value, lower, upper):
    assert wt.bounds(value) == (lower, upper)


@pytest.mark.parametrize("bad", ["24", "2024-13", "2024-5", "2023-02-29", "May 2024", "2024/05", "", None, 2024])
def test_bad_dates_are_rejected(bad):
    with pytest.raises(wt.TimeError):
        wt.bounds(bad)


def test_period_bounds_and_open_end():
    assert wt.period_bounds("2023", "2024-05") == (dt(2023, 1, 1), dt(2024, 6, 1))
    assert wt.period_bounds("2024") == (dt(2024, 1, 1), None)


def test_period_cannot_end_before_it_starts():
    with pytest.raises(wt.TimeError):
        wt.period_bounds("2024-05", "2023")


def test_string_order_would_get_this_wrong():
    """'2024-05' sorts after '2024' as a string, yet lies inside it."""
    assert wt.overlaps(wt.period_bounds("2024-05"), wt.period_bounds("2024", "2024"))


@pytest.mark.parametrize("p, q, expected", [
    ({"start": "2023"}, {"start": "2024-05"}, True),                      # open end runs on
    ({"start": "2020", "end": "2022"}, {"start": "2023"}, False),          # touching years, no overlap
    ({"start": "2020", "end": "2023"}, {"start": "2023-12-31"}, True),
    ({"start": "2024-05", "end": "2024-05"}, {"start": "2024-06"}, False),  # half-open: June is after May
    ({"start": "2021", "end": "2025"}, {"start": "2022", "end": "2022"}, True),  # containment
])
def test_period_overlaps(p, q, expected):
    assert wt.period_overlaps(p, q) is expected
    assert wt.period_overlaps(q, p) is expected


def test_xsd_datetime_is_utc():
    assert wt.xsd_datetime(dt(2024, 5, 1)) == "2024-05-01T00:00:00Z"
