#!/bin/bash
# Build the two initrd variants from the upstream Halium dynparts initrd:
#   initrd-bitra-ecm.img  panic shell over CDC-ECM + telnet instead of RNDIS
#                         (macOS has no RNDIS driver); used for early kernel
#                         bring-up images
#   initrd-bitra-ut.img   the same, plus: skip the OPLUS my_* dynamic
#                         partitions. Used for Ubuntu Touch boots, and for the
#                         debug image (cmdline break=mountroot stops in the
#                         telnet shell, see README.md)
# OUTDIR (default: initrd/) must contain initrd.img-touch-arm64, see
# tools/fetch_inputs.sh.
set -euo pipefail
export LC_ALL=C
TOOLS=$(cd "$(dirname "$0")" && pwd)
OUTDIR=${OUTDIR:-$TOOLS/../initrd}
cd "$OUTDIR"
[ -f initrd.img-touch-arm64 ] || { echo "missing $OUTDIR/initrd.img-touch-arm64" >&2; exit 1; }

rm -rf x work work-ut
mkdir x
(cd x && gzip -dc ../initrd.img-touch-arm64 | cpio -idm --quiet)
cp -a x work
python3 -I "$TOOLS/patch_initrd_telnet.py" work/scripts/panic/telnet
cp -a work work-ut
python3 -I "$TOOLS/patch_initrd_dynparts.py" work-ut/scripts/halium

pack() { (cd "$1" && find . | sort | cpio -o -H newc --quiet) | gzip -9n > "$2"; }
pack work initrd-bitra-ecm.img
pack work-ut initrd-bitra-ut.img
ls -l initrd-bitra-ecm.img initrd-bitra-ut.img
