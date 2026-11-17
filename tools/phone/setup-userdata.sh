#!/bin/sh
# Runs on the phone (Halium initrd debug shell). Formats userdata as ext4 for
# Ubuntu Touch and prepares the bring-up markers. Destroys all data on userdata.
set -e
DEV=/dev/sda11
[ "$(readlink -f /dev/disk/by-partlabel/userdata)" = "$DEV" ] || { echo "ABORT: userdata is not $DEV"; exit 1; }
KB=$(awk '$4=="sda11"{print $3}' /proc/partitions)
[ "$KB" = "237492172" ] || { echo "ABORT: unexpected size $KB"; exit 1; }
grep -q "^$DEV " /proc/mounts && { echo "ABORT: $DEV is mounted"; exit 1; }
echo "formatting $DEV ($KB KiB) as ext4..."
mke2fs -F -t ext4 -L userdata "$DEV"
mkdir -p /mnt/ud
mount -t ext4 "$DEV" /mnt/ud
mkdir -p /mnt/ud/android-data/misc/adb
cp /tmp/adb_keys /mnt/ud/android-data/misc/adb/adb_keys
chmod 0644 /mnt/ud/android-data/misc/adb/adb_keys
touch /mnt/ud/.force-adb
sync
echo "SETUP_OK"; df -h /mnt/ud | tail -1; ls -la /mnt/ud
