#!/usr/bin/env bash
# Chromium kiosk loop: waits for the backend, then keeps the browser alive.
set -u

URL="http://localhost/"
CHROMIUM="$(command -v chromium-browser || command -v chromium)"

# Wait for the backend to come up (fresh boot: migrations may take a moment).
for _ in $(seq 1 120); do
    if curl -sf "http://localhost/api/health" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

while true; do
    "$CHROMIUM" \
        --kiosk "$URL" \
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
        --disable-crash-reporter \
        --autoplay-policy=no-user-gesture-required \
        --check-for-update-interval=31536000 \
        --disk-cache-dir=/tmp/bayta-chromium-cache \
        --disk-cache-size=52428800 \
        --user-data-dir="$HOME/.config/bayta-kiosk"
    # If Chromium exits (crash or nightly kill), pause briefly and relaunch.
    sleep 2
done
