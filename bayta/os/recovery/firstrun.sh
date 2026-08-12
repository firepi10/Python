#!/bin/bash
# Bayta recovery: put a Pi back on the network without re-flashing the card.
#
# Use this when a card was flashed without Imager's Wi-Fi/country settings.
# `custom.toml` cannot help there — it is only read on a card's *first* boot —
# but systemd will run an arbitrary script on *any* boot, which is what the
# cmdline.txt line in this directory's README arranges.
#
#   1. edit WIFI_SSID / WIFI_PASSWORD / WIFI_COUNTRY below
#   2. copy this file to the boot partition as firstrun.sh
#   3. append the systemd.run arguments to cmdline.txt (see README.md)
#
# Runs as root, early, before NetworkManager is up — so the Wi-Fi profile is
# written as a keyfile rather than through nmcli. Removes itself when done.

set +e

WIFI_SSID="YOUR_NETWORK_NAME"
WIFI_PASSWORD="YOUR_WIFI_PASSWORD"
WIFI_COUNTRY="US"

BOOT_DIR=/boot/firmware
[ -d "$BOOT_DIR" ] || BOOT_DIR=/boot
mountpoint -q "$BOOT_DIR" || mount "$BOOT_DIR" 2>/dev/null

# --- Wi-Fi -----------------------------------------------------------------
# Without a regulatory domain the kernel hard-blocks the radio, and every
# attempt to join a network fails before it starts.
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_wifi_country "$WIFI_COUNTRY"
fi
rfkill unblock wifi 2>/dev/null

if [ -x /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_wlan \
        -c "$WIFI_COUNTRY" "$WIFI_SSID" "$WIFI_PASSWORD"
else
    install -d -m 700 /etc/NetworkManager/system-connections
    cat >/etc/NetworkManager/system-connections/preconfigured.nmconnection <<EOF
[connection]
id=preconfigured
type=wifi
autoconnect=true

[wifi]
mode=infrastructure
ssid=$WIFI_SSID

[wifi-security]
key-mgmt=wpa-psk
psk=$WIFI_PASSWORD

[ipv4]
method=auto

[ipv6]
addr-gen-mode=default
method=auto

[proxy]
EOF
    chmod 600 /etc/NetworkManager/system-connections/preconfigured.nmconnection
fi

# --- Clock -----------------------------------------------------------------
# The Pi has no RTC; until this syncs, every wall-clock decision is fiction.
timedatectl set-ntp true 2>/dev/null
systemctl enable systemd-timesyncd 2>/dev/null

# --- Don't let the old build blank the screen again -------------------------
# Cards built before the clock guard landed evaluate the nightly screen-off
# against the image's build time. Turn the schedule off here; the owner can
# switch it back on from Settings once the Pi is updated.
python3 - <<'PY' 2>/dev/null
import json, os, sqlite3

db = "/var/lib/bayta/db/bayta.sqlite3"
if os.path.exists(db):
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO settings(key, value) VALUES('sleep_schedule', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps({"enabled": False, "off": "21:30", "on": "06:30"}),),
    )
    con.commit()
    con.close()
PY

# --- Clean up so this only ever runs once ----------------------------------
# greedy to end of line on purpose: the README appends systemd.run FIRST, so
# everything after it is ours. Trimming only the systemd.run* tokens would
# strand systemd.unit=kernel-command-line.target and boot the Pi into the
# minimal target on every future boot, never reaching Bayta.
sed -i 's| systemd\.run.*||' "$BOOT_DIR/cmdline.txt"
rm -f "$BOOT_DIR/firstrun.sh"
exit 0
