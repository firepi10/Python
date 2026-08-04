# The phone app, from anywhere (Tailscale + PWA)

Bayta's phone app is the same web app the wall runs, installed to your Home
Screen. Tailscale makes it reachable from anywhere, privately — only devices
signed into *your* tailnet can even see it. Free for up to 3 users.

## One-time setup

**On the Pi** (the installer already installed Tailscale):

```bash
sudo tailscale up            # prints a login link — sign in with your account
sudo tailscale serve --bg 80 # serves Bayta over HTTPS inside your tailnet
tailscale status             # note the machine name, e.g. bayta
```

**On each iPhone (you and your wife):**

1. Install **Tailscale** from the App Store and sign in to the same tailnet
   (invite your wife from the Tailscale admin page — Users → Invite).
2. In the Tailscale app, enable **VPN On Demand** so it connects automatically.
3. Open Safari and go to `https://bayta.<your-tailnet>.ts.net`
   (the exact address shows in the Tailscale app under the machine "bayta").
4. Tap **Share → Add to Home Screen**.

That's it. The Bayta icon on your Home Screen now works at home, at work, or on
vacation — upload photos, fix the calendar, add groceries from the store.

## Why this is safe

- Nothing is exposed to the public internet. The `ts.net` address only resolves
  and routes for devices in your tailnet.
- Traffic is end-to-end encrypted by WireGuard (Tailscale) plus HTTPS.
- At home, `http://bayta.local` also works for anyone on your Wi-Fi.
