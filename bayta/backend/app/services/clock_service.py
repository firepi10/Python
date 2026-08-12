"""Is the system clock trustworthy?

The Pi has no battery-backed real-time clock. With no network it restores
whatever timestamp was baked into the image and counts forward from there, so
`datetime.now()` can be hours or days off. Anything that makes the device look
broken based on the wall clock — above all the nightly screen-off — has to ask
here first, or a Pi that never reached Wi-Fi will decide it is 21:30, cut the
HDMI output, and wait for a 06:30 that its clock will never reach.
"""

from pathlib import Path

# systemd-timesyncd creates this the moment it completes its first sync.
SYNC_FLAG = Path("/run/systemd/timesync/synchronized")
TIMESYNC_DIR = SYNC_FLAG.parent


def clock_is_trustworthy() -> bool:
    """True when the clock has been set from the network, or when nothing on
    this machine is responsible for setting it (dev containers, CI, a laptop) —
    there we leave the schedule alone rather than silently disabling it."""
    if SYNC_FLAG.exists():
        return True
    if not TIMESYNC_DIR.exists():
        return True  # no timesyncd here; not a Pi kiosk, don't second-guess
    return False
