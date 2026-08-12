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
    esac
done < "$CONF"

if [ -z "$ssid" ]; then
    log "no ssid= in $CONF; nothing to do"
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
    printf '\n# FAILED to join "%s" on the last boot — check the name and password.\n' \
        "$ssid" >> "$CONF"
fi
exit 0
