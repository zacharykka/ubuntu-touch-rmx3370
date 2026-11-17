#!/bin/bash
# Download everything the build needs that is not in this repository, then
# check it against tools/inputs.sha256 (the exact files the port was built and
# tested with). Existing files are kept.
#
# The UBports CI URLs point at "lastSuccessfulBuild" and move on over time.
# A checksum mismatch therefore means "newer upstream build", not necessarily
# a corrupt download; it is reported but has not been tested on bitra.
set -uo pipefail
cd "$(dirname "$0")/.."
TC=/root/ut-work/toolchains

get() { # dest url
    [ -f "$1" ] && return 0
    mkdir -p "$(dirname "$1")"
    echo "fetching $1"
    curl -fL --retry 3 -o "$1.part" "$2" && mv "$1.part" "$1"
}

toolchain() { # name url
    [ -f "$TC/$1/.done" ] && return 0
    mkdir -p "$TC/$1"
    echo "fetching toolchain $1"
    curl -fsSL --retry 3 "$2" | tar -xz -C "$TC/$1" && touch "$TC/$1/.done"
}

AOSP=https://android.googlesource.com/platform/prebuilts
toolchain clang-r416183b "$AOSP/clang/host/linux-x86/+archive/refs/heads/android12-release/clang-r416183b.tar.gz"
toolchain gcc-aarch64-4.9 "$AOSP/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/+archive/refs/heads/android11-release.tar.gz"
toolchain gcc-arm-4.9 "$AOSP/gcc/linux-x86/arm/arm-linux-androideabi-4.9/+archive/refs/heads/android11-release.tar.gz"

CI=https://ci.ubports.com/job
get userspace/dl/ubuntu-touch-android9plus-rootfs-arm64.tar.gz \
    "$CI/ubuntu-touch-rootfs/job/ubports%252F24.04-2.x/lastSuccessfulBuild/artifact/ubuntu-touch-android9plus-rootfs-arm64.tar.gz"
# Halium 11 GSI: the vendor is VNDK 30 (Android 11 vendor API).
get userspace/dl/h11/halium_halium_arm64.tar.xz \
    "$CI/UBportsCommunityPortsJenkinsCI/job/ubports%252Fporting%252Fcommunity-ports%252Fjenkins-ci%252Fgeneric_arm64/job/halium-11.0/lastSuccessfulBuild/artifact/halium_halium_arm64.tar.xz"
get initrd/initrd.img-touch-arm64 \
    https://github.com/halium/initramfs-tools-halium/releases/download/dynparts/initrd.img-touch-arm64

sha256sum -c tools/inputs.sha256

# Not downloadable: tools/make_test_boot.sh reuses the kernel cmdline of the
# phone's stock boot image, expected as a dump of the boot partition here.
REF=${REF:-/root/ut-work/ref}
[ -f "$REF/boot.img" ] || echo "note: $REF/boot.img (dump of the stock boot partition) is missing" >&2
