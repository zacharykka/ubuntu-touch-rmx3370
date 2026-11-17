#!/bin/sh
# Print a sortable manifest of a mounted rootfs: one line per regular file
# (md5, mode) and per symlink (target). Works with busybox (on the phone) and
# coreutils, so manifests from both sides can be diffed.
#   tools/rootfs_manifest.sh /mnt/rootfs > manifest.txt
cd "$1" || exit 1
L=/tmp/.mf-files.$$
find . -xdev -type f | LC_ALL=C sort > $L
tr "\n" "\0" < $L | xargs -0 md5sum | sed "s/^/F /"
tr "\n" "\0" < $L | xargs -0 stat -c "M %a %n"
find . -xdev -type l | LC_ALL=C sort | while read -r p; do echo "L $p -> $(readlink "$p")"; done
rm -f $L
