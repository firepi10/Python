# Bayta — Hardware Parts List

Target build: a wall-mounted 27" touch family hub (Skylight Cal Max class) driven by the
Raspberry Pi 4B 8GB you already own, framed like a picture, with **zero visible cords**.

## The display (the part that matters most)

Every panel below is a plug-and-play HDMI monitor whose touch layer is standard USB-HID —
it works on Linux with no drivers, no calibration, and none of the laggy Android-tablet feel.

| Tier | Model | Why | ~Price |
|---|---|---|---|
| **Recommended** | **iiyama ProLite T2752MSC-B1** — 27" IPS, 1920×1080, 10-pt projected-capacitive touch, edge-to-edge glass, anti-fingerprint coating | Commercial-grade touch panel (the same class of hardware Skylight builds around). The edge-to-edge glass face is what gives the "premium slab" look; IPS keeps colors/viewing angles gallery-quality on a wall. HDMI + USB touch, VESA 100. | $470–550 |
| Budget alt | ViewSonic TD2760 — 27" VA, 1080p, 10-pt touch | Solid touch, deeper blacks (VA), chunkier bezel — benefits most from framing. | ~$400 |
| No-compromise | Elo 2702L — 27" commercial touch | Elo is what retail/medical kiosks use; the best-feeling glass in the business. | $700+ |

**Why 1080p and not 4K/QHD:** at 27" wall-viewing distance, 1080p is crisp (Skylight's own
27" Cal Max is the same class), and it's precisely the resolution where the Pi 4's GPU
sustains fluid 60 fps animation in Chromium. The only 27" QHD touch panels on the market are
the low-cost no-name brands this build deliberately avoids. Responsiveness *is* the premium feel.

## Mounting & frame

| Part | Pick | ~Price |
|---|---|---|
| Wall mount | Ultra-slim fixed VESA-100 mount (e.g. Mount-It! low-profile, ~1" wall gap) | $20 |
| Frame | **Custom shadow-box / float frame from a local frame shop**, cut to the panel's outer dimensions — wood, mitered corners, no glazing. Bring the monitor's spec-sheet drawing; ask for ~5 mm reveal around the glass. | $100–200 |
| Frame alt | Frame My TV custom surround (made-to-measure, premium finishes, mail-order) | $200+ |
| Frame alt | Frameless — the iiyama's edge-to-edge glass reads as a clean black slab on the wall | $0 |
| Pi case | Flirc Raspberry Pi 4 case — solid aluminum, fanless (the whole case is the heatsink), dead silent. Velcro or screw it behind the panel; it clears a 1" mount gap. | $16 |

## Discreet power (the "no cords" part)

| Part | Pick | ~Price |
|---|---|---|
| In-wall power | **Legrand On-Q In-Wall TV Power Kit (CPT306W-V1)** — creates a code-compliant recessed outlet *behind the frame*, fed through the wall cavity from an existing outlet below. This is the correct, NEC-legal way to hide power (extension cords inside walls are prohibited). Not for fire-rated walls; needs a standard hollow stud bay. | $50–60 |
| Pi PSU | Official Raspberry Pi USB-C power supply (5.1 V / 3 A) — plugs into the recessed outlet next to the monitor's cord | $10 |
| Cables | 1-ft **micro-HDMI → HDMI** (the Pi 4 uses micro-HDMI!), 1-ft USB-B → USB-A for the touch link, right-angle adapters as needed | $25 |

## Storage & extras

| Part | Pick | ~Price |
|---|---|---|
| microSD | SanDisk MAX Endurance 64 GB — endurance-rated cards shrug off years of 24/7 logging | $15 |
| Optional | ddcutil-compatible DDC/CI lets software control hardware backlight brightness on some panels; Bayta falls back to software dimming otherwise | — |

## Total

**≈ $700–900** all-in with the recommended picks (you already have the Pi 4B 8GB).

## Assembly notes

1. Mount the Legrand recessed outlet centered where the panel's back cavity will sit; feed
   from the existing outlet below (its kit includes the through-wall cable and both plates).
2. VESA-mount the panel; velcro the Flirc-cased Pi to the panel's back.
3. Two short cables Pi→panel (micro-HDMI→HDMI, USB-A→USB-B touch), two plugs into the
   recessed outlet. Nothing visible from the front or sides.
4. Hang or attach the shadow-box frame over the panel (most shops add split-batten cleats).
5. Flash the SD per `docs/SETUP_PI.md`, run the installer, and the wall boots into Bayta.
