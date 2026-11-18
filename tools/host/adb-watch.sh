#!/bin/sh
# Watch the host side of the adb link to the bitra port and recover a stalled
# transport.
#
# Why this exists: adb goes offline in two shapes, and only one of them is
# visible from the phone.
#
#   B. the gadget leaves the USB bus  -> the phone fixes this itself
#      (bitra-usb-recover.timer restarts usb-moded); the host just sees the
#      device disappear and come back.
#   A. the gadget is fine, the transport is dead -> the device cannot see this
#      at all. adbd holds its endpoints, the UDC says "configured" and
#      everything on the phone looks healthy, while the host's adb server still
#      lists the device as "offline". This is a host-side stall, and
#      "adb kill-server" has cleared it every time it was tried by hand.
#
# So the phone handles B and this handles A.
#
# Usage:  tools/host/adb-watch.sh [-n] [-i SECONDS] [SERIAL]
#   -n          dry run: report what it would do, change nothing
#   -i SECONDS  poll interval (default 20)
#   SERIAL      only watch this device (default: any device)
#
# Everything it does is host-side: it never touches the phone.
set -u

DRY=0
INTERVAL=20
SERIAL=""
while [ $# -gt 0 ]; do
    case "$1" in
        -n) DRY=1 ;;
        -i) shift; INTERVAL="$1" ;;
        -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "unknown option: $1" >&2; exit 2 ;;
        *) SERIAL="$1" ;;
    esac
    shift
done

# A transport that stays offline across this many consecutive polls is
# considered stalled. Two polls at the default 20s is long enough that a normal
# re-enumeration (which settles in a couple of seconds) never trips it.
OFFLINE_LIMIT=2

log() { echo "$(date '+%H:%M:%S') adb-watch: $*"; }

offline_streak=0
missing_streak=0

adb_state() {
    if [ -n "$SERIAL" ]; then
        adb devices 2>/dev/null | awk -v s="$SERIAL" '$1==s {print $2; exit}'
    else
        adb devices 2>/dev/null | awk 'NR>1 && $1!="" {print $2; exit}'
    fi
}

log "watching (interval ${INTERVAL}s, offline threshold ${OFFLINE_LIMIT} polls)${SERIAL:+, serial $SERIAL}"
while :; do
    state=$(adb_state)

    case "$state" in
        device)
            [ "$offline_streak" -gt 0 ] && log "device is back (was offline for $offline_streak polls)"
            [ "$missing_streak" -gt 0 ] && log "device re-enumerated"
            offline_streak=0
            missing_streak=0
            ;;
        offline|unauthorized)
            offline_streak=$((offline_streak + 1))
            missing_streak=0
            log "state=$state (streak $offline_streak/$OFFLINE_LIMIT)"
            if [ "$offline_streak" -ge "$OFFLINE_LIMIT" ]; then
                if [ "$DRY" = "1" ]; then
                    log "dry run: would restart the adb server"
                else
                    log "transport stalled; restarting the adb server"
                    adb kill-server >/dev/null 2>&1
                    sleep 1
                    adb start-server >/dev/null 2>&1
                    log "restarted; state now: $(adb_state || echo none)"
                fi
                offline_streak=0
            fi
            ;;
        "")
            # No device at all. That is either an unplugged cable or shape B, and
            # in shape B the phone brings itself back, so only report it.
            missing_streak=$((missing_streak + 1))
            offline_streak=0
            [ "$missing_streak" = "1" ] && log "device not present (waiting; shape B recovers on the phone)"
            ;;
    esac

    sleep "$INTERVAL"
done
