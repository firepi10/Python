# Recovering a card that can't reach the network

Symptom: the Pi boots, but it was flashed without Imager's Wi-Fi and country
settings. There's no `bayta.local`, no SSH, no clock — and because the radio has
no regulatory domain, it is hard-blocked by rfkill, so no `nmcli` command can
join a network even if you do get a shell.

`custom.toml` — the file Raspberry Pi Imager writes — **cannot fix this**. It is
read only on a card's *first* boot, and this card has already had one. What does
work on any boot is `systemd.run`, which is the mechanism below.

You only need the FAT boot partition, which is the one macOS and Windows can see.

## 1. Edit the script

Open `firstrun.sh` from this directory and set the three values at the top:

```sh
WIFI_SSID="YOUR_NETWORK_NAME"
WIFI_PASSWORD="YOUR_WIFI_PASSWORD"
WIFI_COUNTRY="US"
```

## 2. Copy it to the card

Put the card in your computer. On macOS the boot partition mounts as
`/Volumes/bootfs` (check `ls /Volumes` if it's named something else).

```bash
cp firstrun.sh /Volumes/bootfs/firstrun.sh
```

## 3. Point the kernel at it

`cmdline.txt` must stay a **single line** — this appends to it without adding a
newline, and keeps a backup:

```bash
cd /Volumes/bootfs
cp cmdline.txt cmdline.txt.bak
printf '%s systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target\n' "$(tr -d '\n' < cmdline.txt)" > cmdline.new
mv cmdline.new cmdline.txt
cat cmdline.txt
```

That `cat` should print one long line ending in `...kernel-command-line.target`.

## 4. Eject and boot

```bash
diskutil eject /Volumes/bootfs
```

Put the card back in the Pi and power on. It boots to a text console, joins
Wi-Fi, sets the clock, reboots itself, and comes up in Bayta. Two reboots, no
keyboard needed.

The script removes itself and its `cmdline.txt` arguments on the way out, so it
never runs twice.

## What it does

- sets the Wi-Fi country and clears the rfkill block
- writes the Wi-Fi credentials as a NetworkManager keyfile (NM isn't running
  that early, so `nmcli` isn't an option)
- turns on NTP so the clock stops being fiction
- disables the nightly screen-off, which on pre-Aug-2026 builds evaluated
  against the image's build time and could blank the panel permanently

## If it doesn't come up

Boot the card, then check from another machine: `ping bayta.local`. Still
nothing? Put the card back in your computer and look at
`/Volumes/bootfs/cmdline.txt` — if it still contains `systemd.run`, the script
never completed, and the likeliest cause is a typo in the SSID or password.
Restore `cmdline.txt.bak`, fix the credentials, and try again.
