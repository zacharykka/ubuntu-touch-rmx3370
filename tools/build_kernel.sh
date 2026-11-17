#!/bin/bash
# Configure and build the bitra Ubuntu Touch kernel (Image + dtbs).
#
#   tools/build_kernel.sh          configure if out/.config is missing, then build
#   tools/build_kernel.sh config   (re)generate the .config only
#   tools/build_kernel.sh build    build with the existing .config
#
# KOUT=/some/dir overrides the output directory (see env.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
. ./env.sh
FRAG=$KSRC/arch/arm64/configs/vendor/halium.config

configure() {
    # The base MUST be kona-perf_defconfig. kona_defconfig enables
    # CONFIG_LRU_GEN, which does not build in this tree
    # (mm/vmscan.c: no member named 'mmap_sem'; block/cfq-iosched.c: bfqd).
    $MK vendor/kona-perf_defconfig
    ARCH=arm64 "$KSRC/scripts/kconfig/merge_config.sh" -m -O "$KOUT" "$KOUT/.config" "$FRAG"
    $MK olddefconfig
    python3 -I tools/check_fragment.py "$FRAG" "$KOUT/.config" | tail -1
}

build() {
    $MK -j"$(nproc)" Image dtbs
    ls -l "$KOUT/arch/arm64/boot/Image" "$KOUT/arch/arm64/boot/dts/vendor/21623/kona-v2.1.dtb"
}

case "${1:-all}" in
    config) configure ;;
    build) build ;;
    all) [ -f "$KOUT/.config" ] || configure; build ;;
    *) echo "usage: $0 [config|build]" >&2; exit 2 ;;
esac
