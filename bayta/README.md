# Bayta

**Bayta** (Aramaic ܒܝܬܐ — *house, household*) is a self-hosted family hub for a wall-mounted
touchscreen, driven by a Raspberry Pi 4B. It mirrors the feature set of commercial smart
family calendars — shared calendar, photos, meal planning, chores, lists — with a premium,
Apple-inspired look and feel, and no subscription.

- **Calendar** — two-way sync with multiple Apple iCloud calendars (CalDAV + app-specific
  passwords), month/week/day views, per-person colors, works offline.
- **Photos** — auto-syncs an iCloud Shared Album; Ken Burns screensaver when idle.
- **Meals** — weekly planner, favorites library, one-tap grocery-list generation.
- **Chores** — recurring chore chart with star rewards.
- **Lists** — shared grocery/to-do/custom lists.
- **Phone app** — installable PWA at `https://bayta.<your-tailnet>.ts.net` (via Tailscale),
  usable from anywhere; also `http://bayta.local` at home.
- **Appliance OS** — Raspberry Pi OS Lite booting straight into a Wayland/Chromium kiosk,
  with daily self-updates and automatic rollback.

## Repo layout

| Path | What |
|---|---|
| `backend/` | FastAPI + SQLite + APScheduler (sync jobs: CalDAV, shared album, weather) |
| `frontend/` | React + Vite + Tailwind kiosk UI and phone admin PWA |
| `os/` | install.sh provisioner, systemd units, kiosk session, boot splash, updater |
| `docs/` | [PARTS.md](docs/PARTS.md) hardware list · SETUP_PI.md · ICLOUD.md · REMOTE.md |
| `scripts/` | dev server, demo seed, screenshot harness |

## Development

```bash
cd bayta
make install     # backend venv + frontend node_modules
make test        # backend pytest
make build       # frontend production build
make dev         # backend :8000 + vite :5173 (proxied)
make screenshot  # headless screenshots of every view → artifacts/
```

## On the Pi

Flash Raspberry Pi OS Lite (64-bit), then see `docs/SETUP_PI.md` — one script takes the
fresh image to a booting Bayta appliance.
