#!/bin/bash -e
# Inside the image chroot: the same installer end users run, in image mode
# (enable services without starting them, file-based hostname, no health probe).
# The repo/branch land in /etc/bayta/update.conf so the flashed device
# self-updates from GitHub.
BAYTA_IMAGE_BUILD=1 BAYTA_SRC_DIR=/opt/bayta-src \
    bash /opt/bayta-src/os/install.sh \
    --repo "https://github.com/firepi10/Python" \
    --branch "claude/skylight-pi-os-build-uel868" \
    --hostname bayta

rm -rf /opt/bayta-src
