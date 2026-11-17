#!/bin/sh
# realme GT Neo2 (bitra): drive usb-moded into its default USB mode once the
# Android container is up.
#
# usb-moded starts early (around t=11s, ordered only After=local-fs/dbus/udev)
# and reaches init-done before the Android container's adbd is available. Its
# appsync step then cannot launch adbd, so it never composes the default mode
# (mtp_adb) and the host sees no adb until the user toggles modes by hand.
#
# Fix: after the container (and ueventd/adbd) are ready, restart usb-moded so
# it re-runs mode composition with appsync satisfied. This is the automated
# equivalent of a manual mode toggle. Never fail hard: a USB problem must not
# hold up boot.
echo "bitra-usb-default-mode: start, uptime $(cut -d' ' -f1 /proc/uptime)"

# Wait for the container to be RUNNING.
i=0
while [ $i -lt 90 ]; do
    state=$(lxc-info -n android -s 2>/dev/null | awk '{print $2}')
    [ "$state" = "RUNNING" ] && break
    i=$((i+1)); sleep 1
done
echo "bitra-usb-default-mode: container state=$state after ${i}s"

# ueventd serves the container; adbd comes up shortly after. Bounded waits.
i=0
while [ $i -lt 60 ] && ! pidof ueventd >/dev/null 2>&1; do i=$((i+1)); sleep 1; done
echo "bitra-usb-default-mode: ueventd pid=$(pidof ueventd) after ${i}s"

# Give the container a moment to export adbd (ffs.adb aliases) before we ask
# usb-moded to compose a mode that needs it.
sleep 3

echo "bitra-usb-default-mode: restarting usb-moded to compose the default mode"
systemctl restart usb-moded
echo "bitra-usb-default-mode: done rc=$?"
exit 0
