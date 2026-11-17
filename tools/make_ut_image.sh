#!/bin/bash
# Build ubuntu.img for realme GT Neo2 (bitra):
#   Ubuntu Touch 24.04-2.x rootfs + Halium 11 GSI (VNDK 30, matches the vendor) + device overlay.
# Mirrors prepare-fake-ota.sh + system-image-from-ota.sh, minus their devel-only
# changes (no empty-password sshd, adbd host-key verification left enabled).
set -euo pipefail
U=/root/ut-work/port-bitra/userspace
OVL=/root/ut-work/port-bitra/device/rootfs-overlay
STAGE=$U/stage
OUT=$U/out
SIZE=${SIZE:-4096M}

rm -rf "$STAGE"; mkdir -p "$STAGE" "$OUT"
tar -xpzf "$U/dl/ubuntu-touch-android9plus-rootfs-arm64.tar.gz" -C "$STAGE" --numeric-owner
tar -xpJf "$U/dl/h11/halium_halium_arm64.tar.xz" -C "$STAGE" --numeric-owner --strip-components=1 system
[ -e "$STAGE/var/lib/lxc/android/system.img" ] && mv "$STAGE/var/lib/lxc/android/system.img" "$STAGE/var/lib/lxc/android/android-rootfs.img"
cp -a "$OVL"/. "$STAGE"/
# The vendor init.qcom.usb.rc would configure the USB gadget from inside the
# Android container and take the controller away from usb-moded. Bind an empty
# file over it (the file comes from the overlay).
LXC_CFG=$STAGE/var/lib/lxc/android/config
grep -q no-usb-init.rc "$LXC_CFG" || cat >> "$LXC_CFG" <<'ENTRY'

# bitra bring-up: the Android side creates /config/usb_gadget/g1 (mass_storage,
# product "Kona for arm64") which steals the USB device controller from
# usb-moded, so the Ubuntu side can expose no ECM/adb interface. Neutralise the
# whole file instead of patching every property trigger in it.
lxc.mount.entry = /var/lib/lxc/android/no-usb-init.rc vendor/etc/init/hw/init.qcom.usb.rc none bind,ro,create=file 0 0
ENTRY
chmod 755 "$STAGE"

rm -f "$OUT/ubuntu.img"
# Kernel 4.19 has no orphan_file support; metadata_csum off as in system-image-from-ota.sh.
mke2fs -q -t ext4 -b 4096 -O ^metadata_csum,^orphan_file -L ubuntu -d "$STAGE" "$OUT/ubuntu.img" "$SIZE"
e2fsck -fn "$OUT/ubuntu.img" >/dev/null
(cd "$OUT" && sha256sum ubuntu.img > ubuntu.img.sha256)
gzip -1 -c "$OUT/ubuntu.img" > "$OUT/ubuntu.img.gz.tmp" && mv "$OUT/ubuntu.img.gz.tmp" "$OUT/ubuntu.img.gz"
ls -la "$OUT"
