#!/usr/bin/env bash
# Apply Wi-Fi settings dropped on the SD card's boot partition.
#
# Runs on every boot. The boot partition is the FAT one that macOS and Windows
# mount automatically, so this is the only way to configure a wall-mounted Pi
# that has no keyboard, no network, and therefore no SSH — without re-flashing.
#
# Drop a file at /boot/firmware/bayta-wifi.txt:
#
#     ssid=MyNetwork
#     password=my-wifi-password      # omit entirely for an open network
#     country=US
#     timezone=America/Chicago       # optional; works on its own too
#
# On success the file is deleted, so the password does not sit in plain text on
# a partition any computer can read. On failure it is left in place with a note
# appended, so a typo can be corrected and retried by rebooting.

set -u

CONF="${BAYTA_WIFI_CONF:-/boot/firmware/bayta-wifi.txt}"
[ -f "$CONF" ] || exit 0

log() { echo "[bayta-netcfg] $*" >&2; }

ssid=""
password=""
country="US"
timezone=""

# tolerate CRLF (edited on a Mac or Windows), blank lines, comments, and spaces
while IFS= read -r raw || [ -n "$raw" ]; do
    line="${raw%$'\r'}"
    case "$line" in ''|'#'*) continue ;; esac
    key="${line%%=*}"
    value="${line#*=}"
    [ "$key" = "$line" ] && continue          # no '=' on the line
    key="$(echo "$key" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
    # only trim the outside; Wi-Fi passwords may legitimately contain spaces
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    case "$key" in
        ssid) ssid="$value" ;;
        password|psk) password="$value" ;;
        country) country="$value" ;;
        timezone|tz) timezone="$value" ;;
    esac
done < "$CONF"

# --- Timezone --------------------------------------------------------------
# Wrong by an hour is wrong: every event on a family calendar is a local time.
tz_done=0
if [ -n "$timezone" ]; then
    if [ ! -f "/usr/share/zoneinfo/$timezone" ]; then
        log "unknown timezone '$timezone'; leaving it alone"
    elif timedatectl set-timezone "$timezone" 2>/dev/null; then
        log "timezone set to $timezone"
        tz_done=1
    else
        # timedated may not be reachable this early; do it by hand
        ln -sf "/usr/share/zoneinfo/$timezone" /etc/localtime
        echo "$timezone" > /etc/timezone
        log "timezone set to $timezone (without timedatectl)"
        tz_done=1
    fi
    # the clock is what the calendar renders against, so restart the backend if
    # it is already up with the old zone loaded
    [ "$tz_done" = 1 ] && systemctl try-restart bayta-backend.service 2>/dev/null
fi

if [ -z "$ssid" ]; then
    if [ "$tz_done" = 1 ]; then
        log "no ssid=; timezone applied, removing $CONF"
        rm -f "$CONF"
    else
        log "nothing to apply from $CONF"
    fi
    exit 0
fi

# Without a regulatory domain the kernel hard-blocks the radio and every
# connect attempt fails before it starts.
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_wifi_country "$country" >/dev/null 2>&1
fi
rfkill unblock wifi >/dev/null 2>&1

nmcli connection delete bayta-wifi >/dev/null 2>&1

log "joining '$ssid'"
if [ -n "$password" ]; then
    nmcli device wifi connect "$ssid" password "$password" name bayta-wifi
else
    nmcli device wifi connect "$ssid" name bayta-wifi
fi
rc=$?

if [ "$rc" -eq 0 ]; then
    log "connected; removing $CONF so the password isn't left on the card"
    rm -f "$CONF"
else
    log "could not join '$ssid' (exit $rc); leaving $CONF in place"
    # Out of range is as likely as a typo — the card gets configured wherever
    # its owner happens to be, and booted somewhere else. Keep the settings and
    # retry every boot; say so rather than blaming the password.
    note="# Could not join \"$ssid\" — out of range here, or the name/password is wrong."
    grep -qF "$note" "$CONF" || printf '\n%s\n# Settings kept; it retries on every boot.\n' \
        "$note" >> "$CONF"
fi
exit 0
