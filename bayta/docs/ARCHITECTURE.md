# Bayta architecture

One Raspberry Pi 4B runs everything: a FastAPI backend (SQLite, background
sync jobs) and a Chromium kiosk rendering the React UI full-screen on the
touchscreen. Phones use the exact same web app — on the LAN via
`bayta.local`, from anywhere via Tailscale — installed as a PWA.

```
┌───────────────────────── Raspberry Pi 4B ─────────────────────────┐
│  labwc (Wayland) ── Chromium --kiosk ── http://localhost/         │
│                                             │                     │
│  uvicorn :80  FastAPI ──────────────────────┤  SSE /api/stream    │
│   ├─ SQLite (WAL, single writer)            │  keeps every        │
│   ├─ APScheduler jobs                       │  client live        │
│   │   ├─ caldav_sync        every 5 min ────┼── iCloud CalDAV     │
│   │   ├─ shared_album_sync  every 30 min ───┼── iCloud shared     │
│   │   ├─ weather_sync       every 15 min ───┼── Open-Meteo        │
│   │   ├─ sleep tick         every minute ── wlopm (screen off/on) │
│   │   └─ occurrence refresh + UI reload  nightly                  │
│   └─ /media/photos (originals / display / thumbs)                 │
│  tailscaled + `tailscale serve 80` → https://bayta.<tn>.ts.net    │
└───────────────────────────────────────────────────────────────────┘
```

## Data flow rules

- **Local-first**: the UI only ever reads SQLite. Sync engines reconcile with
  iCloud in the background; the wall keeps working with no internet.
- **Write-back**: event mutations enqueue `pending_ops`; the sync engine
  pushes them with If-Match etags. A 412 conflict means someone edited the
  same event elsewhere — the server copy wins and is re-pulled.
- **Single writer**: one uvicorn worker, scheduler in-process. SQLite in WAL
  mode with a 5s busy timeout. No other process touches the DB.
- **Auth failures quarantine**: a 401 from iCloud stops retries for that
  account until re-auth (Apple locks accounts after repeated bad attempts).

## GPU budget (VideoCore VI / Chromium)

The premium feel survives on a Pi 4 only if every frame is compositor-cheap:

1. Animate **only** `transform` and `opacity`. Never top/left/width/box-shadow.
2. At most **one** `backdrop-filter` surface on screen at a time (the Sheet).
   Cards are solid surfaces. `reduced_glass` setting kills blur entirely.
3. Screensaver images are pre-sized server-side (2560px long edge) so
   Chromium never decodes/downscales 12MP originals.
4. Ken Burns = one `transform` animation + one `opacity` crossfade on two
   stacked `<img>` layers, `will-change: transform`.
5. 1080p target. Do not drive a 4K panel; the panel recommended in
   PARTS.md is 1920×1080 for exactly this reason.

## Update safety

Daily timer → build new release in a sibling dir → migrate (additive
migrations only) → atomic symlink flip → restart → health-gate → automatic
rollback + quarantine on failure. See `os/update/bayta-update.sh` and
`tests/test_updater.py`.

## SD-card longevity

journald in RAM, Chromium cache on tmpfs, zram swap, WAL checkpointing,
endurance-rated card recommended in PARTS.md.
