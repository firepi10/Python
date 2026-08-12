#!/usr/bin/env bash
# Chromium kiosk loop: waits for the backend, then keeps the browser alive.
set -u

URL="http://localhost/"
HEALTH="http://localhost/api/health"
OFFLINE=/tmp/bayta-offline.html
CHROMIUM="$(command -v chromium-browser || command -v chromium)"

if [ -z "$CHROMIUM" ]; then
    echo "kiosk: no chromium binary found" >&2
    exit 1
fi

# labwc starts this script while it is still bringing the compositor up, so the
# Wayland socket may not exist for another moment. Chromium does not wait — it
# prints "Failed to connect to Wayland display" and exits — so wait here, and
# find the socket by name rather than assuming wayland-0.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
for _ in $(seq 1 30); do
    if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
        break
    fi
    for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$sock" in *.lock) continue ;; esac
        if [ -S "$sock" ]; then
            WAYLAND_DISPLAY="$(basename "$sock")"
            export WAYLAND_DISPLAY
            break
        fi
    done
    [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] && break
    sleep 1
done
echo "kiosk: using WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset} in $XDG_RUNTIME_DIR" >&2

healthy() { curl -sf "$HEALTH" >/dev/null 2>&1; }

# Chromium derives its crash-database path from $HOME and asserts rather than
# degrades when it comes out empty: crashpad launches with no --database, hits
# NOTREACHED, and takes the zygote down with "Check failed: . : Broken pipe".
# The browser never opens and the wall goes black. Never leave that to chance —
# pin HOME from the passwd entry, and hand Chromium directories that exist.
if [ -z "${HOME:-}" ] || [ ! -d "${HOME:-}" ]; then
    HOME="$(getent passwd "$(id -u)" | cut -d: -f6)"
    export HOME
    echo "kiosk: HOME was unusable; using $HOME" >&2
fi
PROFILE_DIR="$HOME/.config/bayta-kiosk"
CRASH_DIR=/tmp/bayta-crash
if ! mkdir -p "$PROFILE_DIR" 2>/dev/null; then
    # a read-only or full home is not worth dying over; /tmp is tmpfs here
    PROFILE_DIR=/tmp/bayta-kiosk-profile
    mkdir -p "$PROFILE_DIR"
    echo "kiosk: $HOME/.config is not writable; profile in $PROFILE_DIR" >&2
fi
mkdir -p "$CRASH_DIR"

# The panel is the only output this machine has. A blank screen is the one
# outcome that tells its owner nothing, so when the backend is missing we say
# so on the glass rather than loading a URL that will not answer.
write_offline_page() {
    cat > "$OFFLINE" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Bayta</title>
<style>
 html,body{margin:0;height:100%;background:#101014;color:#f5f5f7;
   font:16px/1.6 system-ui,sans-serif;display:grid;place-items:center}
 .b{max-width:62ch;padding:40px}
 h1{font-size:34px;font-weight:600;margin:8px 0 12px}
 code{background:rgba(255,255,255,.08);padding:2px 7px;border-radius:6px}
 .t{font-size:13px;letter-spacing:.08em;opacity:.6}
 li{margin:8px 0}
</style>
<div class=b>
 <div class=t>BAYTA</div>
 <h1>The display works — the app hasn't started</h1>
 <p>The screen, the compositor and the browser are all fine. The Bayta
    service didn't answer within two minutes of boot, so there is nothing
    to show yet.</p>
 <p>From another computer on the same network:</p>
 <ul>
  <li><code>ssh pi@bayta.local</code> &nbsp;(password <code>bayta</code>)</li>
  <li><code>systemctl status bayta-backend</code></li>
  <li><code>journalctl -u bayta-backend -n 50</code></li>
 </ul>
 <p>This screen swaps itself for Bayta automatically, within a few seconds
    of the service coming up. No need to reboot.</p>
</div>
HTML
}

# Fresh boot: migrations and the first import take a moment.
for _ in $(seq 1 120); do
    healthy && break
    sleep 1
done

while true; do
    if healthy; then
        target="$URL"
    else
        write_offline_page
        target="file://$OFFLINE"
    fi

    "$CHROMIUM" \
        --kiosk "$target" \
        --ozone-platform=wayland \
        --enable-gpu-rasterization \
        --ignore-gpu-blocklist \
        --enable-zero-copy \
        --touch-events=enabled \
        --disable-pinch \
        --overscroll-history-navigation=0 \
        --noerrdialogs \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-features=TranslateUI \
        --autoplay-policy=no-user-gesture-required \
        --check-for-update-interval=31536000 \
        --disk-cache-dir=/tmp/bayta-chromium-cache \
        --disk-cache-size=52428800 \
        --crash-dumps-dir="$CRASH_DIR" \
        --user-data-dir="$PROFILE_DIR" &
    chromium_pid=$!

    # Showing the fallback: the page can't poll localhost itself (a file://
    # origin is cross-origin to http://localhost), so watch from out here and
    # restart into the real UI the moment the backend answers.
    if [ "$target" != "$URL" ]; then
        while kill -0 "$chromium_pid" 2>/dev/null; do
            if healthy; then
                kill "$chromium_pid" 2>/dev/null
                break
            fi
            sleep 5
        done
    fi

    wait "$chromium_pid"
    # If Chromium exits (crash or nightly kill), pause briefly and relaunch.
    sleep 2
done
