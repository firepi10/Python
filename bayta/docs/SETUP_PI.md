# Setting up the Pi

What you need: the Raspberry Pi 4B, the microSD card, a computer with an SD reader,
and your Wi-Fi password. Total hands-on time: about 15 minutes plus install time.

## 1. Flash the OS

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer.
2. Choose **Raspberry Pi OS Lite (64-bit)** (under "Raspberry Pi OS (other)").
3. Click the gear / "Edit settings" before writing and set:
   - hostname: `bayta`
   - username: `pi`, a password you'll remember
   - your Wi-Fi network + country
   - enable SSH (password auth is fine)
4. Write the card, put it in the Pi, connect the touchscreen (micro-HDMI + USB
   touch cable), and power it on.

## 2. Run the installer

From your computer's terminal:

```bash
ssh pi@bayta.local
# then on the Pi:
curl -fsSL https://raw.githubusercontent.com/firepi10/Python/claude/skylight-pi-os-build-uel868/bayta/os/install.sh \
  | sudo bash -s -- \
      --repo https://github.com/firepi10/Python \
      --branch claude/skylight-pi-os-build-uel868 \
      --rotation normal          # or 90 / 270 for portrait
```

The installer sets up everything: packages, the Bayta services, the kiosk session,
quiet boot with the Bayta splash, mDNS, log-to-RAM (SD card protection), and
Tailscale. When it finishes:

```bash
sudo tailscale up          # sign in once in the browser link it prints
sudo tailscale serve --bg 80
sudo reboot
```

The Pi boots straight into Bayta on the touchscreen.

## 3. First-boot checklist

On the wall screen or from your phone at `http://bayta.local`:

- [ ] **Settings → Family**: add each of you with a color.
- [ ] **Settings → iCloud calendars → Add account**: sign in with an
      [app-specific password](ICLOUD.md) and map calendars to people.
      Verify: add an event on your iPhone → it appears on the wall within
      ~5 minutes; add one on the wall → it appears on your iPhone.
- [ ] **Photos → iCloud album**: paste your shared-album link ([how](ICLOUD.md)).
- [ ] **Settings → Display & sleep**: set the night schedule; verify the panel
      turns off at the "off" time and a touch wakes it.
- [ ] Leave it idle past the timeout → the photo screensaver starts.
- [ ] On both iPhones: [set up Tailscale + Add to Home Screen](REMOTE.md);
      verify photo upload works with Wi-Fi off (cellular).

## Troubleshooting

| Symptom | Check |
|---|---|
| Blank screen | `ssh pi@bayta.local` → `sudo systemctl status bayta-backend`, `journalctl -u bayta-backend -n 50` |
| Touch works but misaligned in portrait | Settings → rotation is applied by the compositor; re-check the value, then reboot |
| bayta.local not found | Give it a minute after boot; ensure your phone is on the same Wi-Fi; try the Pi's IP |
| Events not syncing | Settings → the account card shows the exact error; 99% of the time it's a regular password where an app-specific one belongs |
