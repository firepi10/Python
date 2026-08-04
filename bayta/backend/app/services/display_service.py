"""Display power + rotation control for the kiosk.

The backend and the labwc kiosk session run as the same user, so these
helpers can talk to the compositor's Wayland socket directly — no sudo.
On machines without the tools (the dev container), everything no-ops.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TRANSFORMS = ("normal", "90", "180", "270")

_display_on = True


def _wayland_env() -> dict:
    env = dict(os.environ)
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    return env


def _run(cmd: list[str]) -> bool:
    if shutil.which(cmd[0]) is None:
        logger.debug("%s not installed; skipping", cmd[0])
        return False
    try:
        subprocess.run(cmd, env=_wayland_env(), check=True, capture_output=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.warning("display command failed: %s (%s)", cmd, exc)
        return False


def display_off() -> bool:
    global _display_on
    ok = _run(["wlopm", "--off", "*"])
    if ok:
        _display_on = False
    return ok


def display_on() -> bool:
    global _display_on
    ok = _run(["wlopm", "--on", "*"])
    if ok:
        _display_on = True
    return ok


def is_display_on() -> bool:
    return _display_on


def rotation_file() -> Path:
    return get_settings().data_dir / "rotation"


def set_rotation(transform: str) -> bool:
    """Persist the rotation (read by the kiosk session at boot) and apply it
    live when wlr-randr is present."""
    if transform not in TRANSFORMS:
        raise ValueError(f"transform must be one of {TRANSFORMS}")
    rotation_file().parent.mkdir(parents=True, exist_ok=True)
    rotation_file().write_text(transform + "\n")
    applied = False
    output = _detect_output()
    if output:
        applied = _run(["wlr-randr", "--output", output, "--transform", transform])
    return applied


def _detect_output() -> str | None:
    if shutil.which("wlr-randr") is None:
        return None
    try:
        result = subprocess.run(
            ["wlr-randr"], env=_wayland_env(), capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if line and not line.startswith(" "):
                return line.split()[0]
    except (subprocess.SubprocessError, OSError):
        pass
    return None
