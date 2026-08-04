#!/bin/bash -e
# Host side: drop the Bayta source (with prebuilt frontend) into the image.
# The CI workflow fills files/bayta before the build starts.
rm -rf "${ROOTFS_DIR}/opt/bayta-src"
mkdir -p "${ROOTFS_DIR}/opt/bayta-src"
cp -a files/bayta/. "${ROOTFS_DIR}/opt/bayta-src/"
