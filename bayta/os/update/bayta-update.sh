#!/usr/bin/env bash
# Bayta self-update (runs daily via bayta-update.timer, or on demand).
#
# Channels (configured in /etc/bayta/update.conf):
#   RELEASE_JSON_URL=...  tarball channel: a latest.json with
#                         {"version": "...", "url": "...", "sha256": "..."}
#   REPO_URL=... BRANCH=  git channel: track a branch (default for
#                         source installs)
#
# Flow: fetch new version -> build alongside the running one -> migrate DB ->
# atomically flip the `current` symlink -> restart -> health-gate -> roll back
# to the previous release automatically if the new one doesn't come up.
#
# Env knobs (used by tests; production uses the defaults):
#   BAYTA_ROOT (/opt/bayta)  BAYTA_ETC (/etc/bayta)
#   SYSTEMCTL (systemctl)    HEALTH_CMD (curl -sf http://localhost/api/health)
#   BAYTA_SKIP_BUILD (unset) HEALTH_TRIES (30)
set -euo pipefail

ROOT="${BAYTA_ROOT:-/opt/bayta}"
ETC="${BAYTA_ETC:-/etc/bayta}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
HEALTH_CMD="${HEALTH_CMD:-curl -sf http://localhost/api/health && curl -sf -o /dev/null http://localhost/}"
HEALTH_TRIES="${HEALTH_TRIES:-30}"

# logs go to stderr: the fetch_* functions communicate the new release path
# over stdout (command substitution), so stdout must stay clean
log() { printf '[bayta-update] %s\n' "$*" >&2; }

[ -f "$ETC/update.conf" ] && . "$ETC/update.conf"
RELEASE_JSON_URL="${RELEASE_JSON_URL:-}"
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"

current_target() { readlink -f "$ROOT/current" 2>/dev/null || true; }

build_release() {
    local dest="$1"
    if [ -n "${BAYTA_SKIP_BUILD:-}" ]; then
        return 0
    fi
    # explicit `|| return 1` throughout: the caller invokes this in an `if`,
    # which suspends errexit inside the function
    python3 -m venv "$dest/venv" || return 1
    "$dest/venv/bin/pip" install -q --upgrade pip --cache-dir "$ROOT/shared/pip-cache" || return 1
    "$dest/venv/bin/pip" install -q "$dest/backend" --cache-dir "$ROOT/shared/pip-cache" || return 1
    if [ ! -d "$dest/frontend/dist" ]; then
        # image installs ship no node at all — a source update must bring it,
        # same as install.sh's build_frontend does. The toolchain needs
        # node >= 20 (react-router 7 refuses less; tailwind's native binding
        # fails to resolve under bookworm's node 18 npm), so use NodeSource.
        local node_major=0
        command -v node >/dev/null 2>&1 && node_major="$(node -p 'process.versions.node.split(".")[0]')"
        if [ "$node_major" -lt 20 ] || ! command -v npm >/dev/null 2>&1; then
            log "installing node 22 for the frontend build (found ${node_major})"
            apt-get purge -y -qq npm >/dev/null 2>&1 || true
            curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 || return 1
            apt-get install -y -qq nodejs >/dev/null || return 1
        fi
        (cd "$dest/frontend" && npm install --no-audit --no-fund >/dev/null && npm run build >/dev/null) || return 1
    fi
    if [ ! -f "$dest/frontend/dist/index.html" ]; then
        log "frontend build produced no dist — refusing to ship a release without a UI"
        return 1
    fi
    (cd "$dest/backend" && BAYTA_DATA_DIR=/var/lib/bayta "$dest/venv/bin/alembic" upgrade head) || return 1
}

fetch_git() {
    local sha dest
    sha="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" | cut -f1)"
    if [ -z "$sha" ]; then
        log "could not resolve $BRANCH on $REPO_URL"
        return 1
    fi
    local cur
    cur="$(cat "$(current_target)/.git-sha" 2>/dev/null || true)"
    if [ "$sha" = "$cur" ]; then
        log "up to date ($sha)"
        return 0
    fi
    # sha-keyed dir: a release that failed its health gate stays quarantined
    dest="$ROOT/releases/git-${sha:0:12}"
    if [ -e "$dest/.bad" ]; then
        log "release $sha previously failed; skipping"
        return 0
    fi
    rm -rf "$dest"
    log "updating to $sha"
    local tmp
    tmp="$(mktemp -d)"
    git clone -q --depth 1 --branch "$BRANCH" "$REPO_URL" "$tmp/src" 2>/dev/null
    mv "$tmp/src/bayta" "$dest"
    rm -rf "$tmp"
    echo "$sha" > "$dest/.git-sha"
    echo "$dest"
}

fetch_tarball() {
    local json version url sha dest
    json="$(curl -fsSL "$RELEASE_JSON_URL")"
    version="$(echo "$json" | jq -r .version)"
    url="$(echo "$json" | jq -r .url)"
    sha="$(echo "$json" | jq -r .sha256)"
    local cur_version
    cur_version="$(cat "$(current_target)/VERSION" 2>/dev/null || true)"
    if [ "$version" = "$cur_version" ]; then
        log "up to date ($version)"
        return 0
    fi
    dest="$ROOT/releases/v$version"
    if [ -e "$dest/.bad" ]; then
        log "release $version previously failed; skipping"
        return 0
    fi
    rm -rf "$dest"
    log "updating to $version"
    local tmp
    tmp="$(mktemp -d)"
    curl -fsSL "$url" -o "$tmp/bayta.tar.gz"
    echo "$sha  $tmp/bayta.tar.gz" | sha256sum -c - >/dev/null
    mkdir -p "$dest"
    tar -xzf "$tmp/bayta.tar.gz" -C "$dest" --strip-components=1
    rm -rf "$tmp"
    echo "$dest"
}

main() {
    mkdir -p "$ROOT/releases" "$ROOT/shared"
    local previous new_release
    previous="$(current_target)"

    if [ -n "$RELEASE_JSON_URL" ]; then
        new_release="$(fetch_tarball)"
    elif [ -n "$REPO_URL" ]; then
        new_release="$(fetch_git)"
    else
        log "no update channel configured in $ETC/update.conf"
        exit 0
    fi
    if [ -z "$new_release" ] || [ ! -d "$new_release" ]; then
        exit 0
    fi

    if ! build_release "$new_release"; then
        log "build FAILED — quarantining $new_release, keeping the current release"
        touch "$new_release/.bad" 2>/dev/null || true
        exit 1
    fi

    log "switching to $new_release"
    ln -sfn "$new_release" "$ROOT/current.tmp"
    mv -T "$ROOT/current.tmp" "$ROOT/current"
    $SYSTEMCTL restart bayta-backend

    local healthy=0
    for _ in $(seq 1 "$HEALTH_TRIES"); do
        if eval "$HEALTH_CMD" >/dev/null 2>&1; then
            healthy=1
            break
        fi
        sleep 2
    done

    if [ "$healthy" = 1 ]; then
        log "update healthy"
        # prune: keep current + previous + one spare
        ls -dt "$ROOT/releases"/*/ 2>/dev/null | tail -n +4 | while read -r old; do
            case "$(readlink -f "$old")" in
                "$(current_target)"|"$previous") ;;
                *) rm -rf "$old" ;;
            esac
        done
        exit 0
    fi

    log "health check FAILED — rolling back"
    touch "$new_release/.bad" 2>/dev/null || true
    if [ -n "$previous" ] && [ -d "$previous" ]; then
        ln -sfn "$previous" "$ROOT/current.tmp"
        mv -T "$ROOT/current.tmp" "$ROOT/current"
        $SYSTEMCTL restart bayta-backend
    fi
    exit 1
}

main "$@"
