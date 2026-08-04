"""Nightly screen-off schedule."""

from datetime import datetime, time


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def should_be_asleep(now: datetime, off: str, on: str) -> bool:
    """True when `now` falls inside the off-window. Handles windows that
    wrap midnight (21:30 -> 06:30) and same-day windows alike."""
    t = now.time()
    t_off = parse_hhmm(off)
    t_on = parse_hhmm(on)
    if t_off == t_on:
        return False
    if t_off < t_on:  # same-day window (rare: nap-time style)
        return t_off <= t < t_on
    return t >= t_off or t < t_on  # wraps midnight
