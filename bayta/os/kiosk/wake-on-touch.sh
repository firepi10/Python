#!/usr/bin/env bash
# While the sleep schedule has the panel off, the first touch wakes it.
# (Tapping also resets the backend's idle state via the UI itself.)
set -u

command -v libinput >/dev/null 2>&1 || exit 0
command -v wlopm >/dev/null 2>&1 || exit 0

libinput debug-events 2>/dev/null | while read -r line; do
    case "$line" in
        *TOUCH_DOWN*|*POINTER_BUTTON*)
            # cheap check: only issue wlopm when something is actually off
            if wlopm 2>/dev/null | grep -q "off"; then
                wlopm --on '*' >/dev/null 2>&1
            fi
            ;;
    esac
done
