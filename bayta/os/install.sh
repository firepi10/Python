#!/usr/bin/env bash
# Bayta installer: fresh Raspberry Pi OS Lite (64-bit, Bookworm) -> wall appliance.
#
#   curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/<branch>/bayta/os/install.sh \
#     | sudo bash -s -- --repo https://github.com/<owner>/<repo> --branch <branch>
#
# Flags:
#   --repo URL        git repository to install from (required for --from-source)
#   --branch NAME     branch to install (default: main)
#   --rotation N      normal|90|180|270 (default: normal)
#   --hostname NAME   mDNS hostname (default: bayta -> http://bayta.local)
#   --no-tailscale    skip Tailscale installation
#   --no-kiosk        backend only (no Chromium kiosk session)
#   --dry-run         print actions without changing anything
set -euo pipefail

REPO_URL=""
BRANCH="main"
ROTATION="normal"
NEW_HOSTNAME="bayta"
WITH_TAILSCALE=1
WITH_KIOSK=1
DRY_RUN=0

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO_URL="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --rotation) ROTATION="$2"; shift 2 ;;
        --hostname) NEW_HOSTNAME="$2"; shift 2 ;;
        --no-tailscale) WITH_TAILSCALE=0; shift ;;
        --no-kiosk) WITH_KIOSK=0; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

log() { printf '\033[1;34m[bayta]\033[0m %s\n' "$*"; }
run() {
    if [ "$DRY_RUN" = 1 ]; then
        echo "DRY-RUN: $*"
    else
        "$@"
    fi
}

require_root() {
    if [ "$(id -u)" != 0 ]; then
        echo "run me with sudo" >&2
        exit 1
    fi
}

check_platform() {
    if [ "$DRY_RUN" = 1 ]; then return; fi
    if [ "$(uname -m)" != "aarch64" ]; then
        echo "expected 64-bit Raspberry Pi OS (aarch64), found $(uname -m)" >&2
        exit 1
    fi
    if ! grep -q "bookworm\|trixie" /etc/os-release; then
        echo "expected Raspberry Pi OS Bookworm or newer" >&2
        exit 1
    fi
}

install_packages() {
    log "installing packages"
    export DEBIAN_FRONTEND=noninteractive
    run apt-get update -qq
    run apt-get install -y -qq \
        git curl jq avahi-daemon \
        python3-venv python3-pip \
        chromium-browser labwc wlr-randr seatd libinput-tools \
        plymouth plymouth-themes \
        zram-tools unattended-upgrades \
        fonts-noto-color-emoji || true
    # wlopm is tiny and sometimes missing from the repos; best effort
    run apt-get install -y -qq wlopm || log "wlopm unavailable; sleep mode will be limited"
}

create_user() {
    if ! id bayta >/dev/null 2>&1; then
        log "creating user bayta"
        run useradd -m -s /bin/bash bayta
    fi
    run usermod -aG video,render,input,tty bayta
    run loginctl enable-linger bayta || true
}

setup_dirs() {
    log "creating directories"
    run install -d -o bayta -g bayta /opt/bayta /opt/bayta/releases /opt/bayta/shared
    run install -d -o bayta -g bayta /var/lib/bayta /var/lib/bayta/db /var/lib/bayta/photos
    run install -d -o bayta -g bayta -m 700 /var/lib/bayta/secrets
    run install -d /etc/bayta
    if [ ! -f /etc/bayta/bayta.env ]; then
        run bash -c 'echo "# Bayta environment overrides" > /etc/bayta/bayta.env'
    fi
    if [ -n "$REPO_URL" ]; then
        run bash -c "printf 'REPO_URL=%s\nBRANCH=%s\n' '$REPO_URL' '$BRANCH' > /etc/bayta/update.conf"
    fi
}

fetch_source() {
    log "fetching Bayta ($BRANCH)"
    if [ -z "$REPO_URL" ]; then
        echo "--repo is required" >&2
        exit 2
    fi
    local dest="/opt/bayta/releases/git-$(date +%Y%m%d%H%M%S)"
    run git clone --depth 1 --branch "$BRANCH" "$REPO_URL" /tmp/bayta-src
    run bash -c "mv /tmp/bayta-src/bayta '$dest' && rm -rf /tmp/bayta-src"
    run chown -R bayta:bayta "$dest"
    run ln -sfn "$dest" /opt/bayta/current
}

build_backend() {
    log "building backend venv"
    run sudo -u bayta python3 -m venv /opt/bayta/current/venv
    run sudo -u bayta /opt/bayta/current/venv/bin/pip install -q --upgrade pip
    run sudo -u bayta /opt/bayta/current/venv/bin/pip install -q /opt/bayta/current/backend
}

build_frontend() {
    # Releases ship a prebuilt frontend; a source install builds it once here.
    if [ -d /opt/bayta/current/frontend/dist ]; then
        log "frontend already built"
        return
    fi
    log "building frontend (installing node)"
    if ! command -v npm >/dev/null 2>&1; then
        run apt-get install -y -qq nodejs npm
    fi
    run sudo -u bayta bash -c "cd /opt/bayta/current/frontend && npm install --no-audit --no-fund && npm run build"
}

install_services() {
    log "installing systemd units"
    run cp /opt/bayta/current/os/systemd/bayta-backend.service /etc/systemd/system/
    run cp /opt/bayta/current/os/systemd/bayta-update.service /etc/systemd/system/
    run cp /opt/bayta/current/os/systemd/bayta-update.timer /etc/systemd/system/
    run cp /opt/bayta/current/os/config/journald-bayta.conf /etc/systemd/journald.conf.d/bayta.conf 2>/dev/null || {
        run install -d /etc/systemd/journald.conf.d
        run cp /opt/bayta/current/os/config/journald-bayta.conf /etc/systemd/journald.conf.d/bayta.conf
    }
    run cp /opt/bayta/current/os/config/avahi-bayta.service /etc/avahi/services/bayta.service
    # allow the backend's "Update now" button to start the update unit
    run bash -c 'echo "bayta ALL=(root) NOPASSWD: /usr/bin/systemctl start bayta-update.service" > /etc/sudoers.d/bayta && chmod 440 /etc/sudoers.d/bayta'
    run systemctl daemon-reload
    run systemctl enable --now bayta-backend.service bayta-update.timer avahi-daemon
}

setup_kiosk() {
    [ "$WITH_KIOSK" = 1 ] || return 0
    log "configuring kiosk session"
    run install -o bayta -g bayta /opt/bayta/current/os/kiosk/bash_profile /home/bayta/.bash_profile
    run install -d -o bayta -g bayta /home/bayta/.config/labwc
    run install -o bayta -g bayta /opt/bayta/current/os/kiosk/labwc-autostart /home/bayta/.config/labwc/autostart
    run chmod +x /opt/bayta/current/os/kiosk/kiosk-run.sh /opt/bayta/current/os/kiosk/wake-on-touch.sh
    run bash -c "echo '$ROTATION' > /var/lib/bayta/rotation && chown bayta:bayta /var/lib/bayta/rotation"
    # console autologin on tty1 as bayta
    run install -d /etc/systemd/system/getty@tty1.service.d
    run bash -c 'cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin bayta --noclear %I \$TERM
EOF'
}

setup_boot_polish() {
    [ "$WITH_KIOSK" = 1 ] || return 0
    log "quiet boot + splash"
    local cmdline=/boot/firmware/cmdline.txt
    [ -f "$cmdline" ] || cmdline=/boot/cmdline.txt
    if [ -f "$cmdline" ] && ! grep -q "quiet" "$cmdline"; then
        run sed -i 's/$/ quiet splash loglevel=0 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles/' "$cmdline"
    fi
    local config=/boot/firmware/config.txt
    [ -f "$config" ] || config=/boot/config.txt
    if [ -f "$config" ] && ! grep -q "disable_splash" "$config"; then
        run bash -c "printf '\ndisable_splash=1\nboot_delay=0\n' >> '$config'"
    fi
    if [ -d /opt/bayta/current/os/plymouth/bayta ]; then
        run cp -r /opt/bayta/current/os/plymouth/bayta /usr/share/plymouth/themes/
        run plymouth-set-default-theme -R bayta || true
    fi
}

setup_hostname() {
    log "hostname -> $NEW_HOSTNAME (http://$NEW_HOSTNAME.local)"
    run hostnamectl set-hostname "$NEW_HOSTNAME"
    run sed -i "s/127.0.1.1.*/127.0.1.1\t$NEW_HOSTNAME/" /etc/hosts || true
}

setup_tailscale() {
    [ "$WITH_TAILSCALE" = 1 ] || return 0
    if ! command -v tailscale >/dev/null 2>&1; then
        log "installing Tailscale"
        run bash -c "curl -fsSL https://tailscale.com/install.sh | sh"
    fi
}

migrate_and_check() {
    log "running database migrations"
    run sudo -u bayta bash -c "cd /opt/bayta/current/backend && BAYTA_DATA_DIR=/var/lib/bayta /opt/bayta/current/venv/bin/alembic upgrade head"
    if [ "$DRY_RUN" = 0 ]; then
        for _ in $(seq 1 30); do
            if curl -sf http://localhost/api/health >/dev/null 2>&1; then
                log "backend healthy"
                return
            fi
            sleep 1
        done
        log "WARNING: backend did not answer /api/health yet; check: journalctl -u bayta-backend"
    fi
}

finish() {
    cat <<EOF

  ─────────────────────────────────────────────────────────
   Bayta is installed.

   On this network:   http://$NEW_HOSTNAME.local
   From anywhere:     1) sudo tailscale up      (sign in once)
                      2) sudo tailscale serve --bg 80
                      3) use https://$NEW_HOSTNAME.<your-tailnet>.ts.net
                         and Add to Home Screen on both iPhones

   Kiosk starts on the next reboot:   sudo reboot
  ─────────────────────────────────────────────────────────
EOF
}

require_root
check_platform
install_packages
create_user
setup_dirs
fetch_source
build_backend
build_frontend
install_services
setup_kiosk
setup_boot_polish
setup_hostname
setup_tailscale
migrate_and_check
finish
