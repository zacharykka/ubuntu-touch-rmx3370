#!/bin/sh
# realme GT Neo2 (bitra): recover the USB gadget when it drops off the bus.
#
# Two failure modes have been seen on this port, and adbd never self-heals
# either one (its USB loop only handles BIND/ENABLE/DISABLE/UNBIND/SETUP, so a
# dropped transport or a re-composed gadget leaves adb dead until something
# restarts it):
#
#   A. the phone is still enumerated on the host bus but adb reports "offline";
#   B. the phone disappears from the host bus entirely.
#
# Mode B is the one the device can act on, and it is detectable: the cable is
# still supplying VBUS (power_supply/usb/present = 1) but the gadget is no
# longer attached to the UDC. Restarting usb-moded re-composes the gadget and
# has recovered this every time it was done by hand.
#
# Guards, so this never fights a normal boot or a deliberate unplug:
#   - present must be 1 (a cable is connected; we do not care about charging
#     bricks because those do not enumerate either, but they also never show
#     present=1 with a data role, so the extra check keeps it honest);
#   - the bad state must persist across two consecutive samples;
#   - at most one recovery per RECOVER_MIN_INTERVAL seconds;
#   - nothing happens in the first BOOT_GRACE seconds after boot, when the
#     gadget is still being composed.
#
# Usage (from the timer): usb-recover.sh
# Manual check:            usb-recover.sh --dry-run
set -u

UDC=/sys/class/udc/a600000.dwc3/state
GADGET_UDC=/sys/kernel/config/usb_gadget/g1/UDC
PRESENT=/sys/class/power_supply/usb/present
STAMP=/run/bitra-usbrecover.stamp

BOOT_GRACE=90
RECOVER_MIN_INTERVAL=120
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { echo "bitra-usb-recover: $*"; }

up=$(cut -d' ' -f1 /proc/uptime | cut -d. -f1)
if [ "$up" -lt "$BOOT_GRACE" ]; then
    exit 0
fi

present=$(cat "$PRESENT" 2>/dev/null || echo 0)
[ "$present" = "1" ] || exit 0

# A gadget that is attached to the UDC reports "configured" or "addressed";
# "not attached" (or an empty UDC file) while VBUS is present means the gadget
# left the bus.
gadget_udc=$(cat "$GADGET_UDC" 2>/dev/null)
udc_state=$(cat "$UDC" 2>/dev/null)

bad=0
if [ -z "$gadget_udc" ]; then
    bad=1
elif [ "$udc_state" = "not attached" ]; then
    bad=1
fi

[ "$bad" = "1" ] || exit 0

# Require the bad state to persist, so a transient re-enumeration is ignored.
sleep 3
gadget_udc=$(cat "$GADGET_UDC" 2>/dev/null)
udc_state=$(cat "$UDC" 2>/dev/null)
if [ -n "$gadget_udc" ] && [ "$udc_state" != "not attached" ]; then
    exit 0
fi

now=$(cut -d' ' -f1 /proc/uptime | cut -d. -f1)
if [ -e "$STAMP" ]; then
    last=$(cat "$STAMP" 2>/dev/null || echo 0)
    if [ $((now - last)) -lt "$RECOVER_MIN_INTERVAL" ]; then
        log "gadget down (udc=${udc_state:-none} gadget=${gadget_udc:-unbound}) but last recovery was $((now - last))s ago; waiting"
        exit 0
    fi
fi

log "gadget off the bus (present=1 udc=${udc_state:-none} gadget=${gadget_udc:-unbound}); re-composing"
if [ "$DRY_RUN" = "1" ]; then
    log "dry run: would restart usb-moded"
    exit 0
fi

echo "$now" > "$STAMP"
systemctl restart usb-moded
log "usb-moded restarted (rc=$?)"

# Give it a moment and report what happened, for the journal record.
sleep 5
log "after: udc=$(cat "$UDC" 2>/dev/null) gadget=$(cat "$GADGET_UDC" 2>/dev/null) adbd=$(pidof adbd || echo none)"
