#!/bin/bash
# Assemble a test boot image: our kernel + kona-v2.1.dtb + patched Halium initrd.
# usage: make_test_boot.sh OUT.img "EXTRA CMDLINE"
set -euo pipefail
cd /root/ut-work/port-bitra
OUT=$1; EXTRA=$2
STOCK_CMDLINE=$(python3 -I -c "print(open(\"/root/ut-work/ref/boot.img\",\"rb\").read(4096)[64:576].rstrip(b\"\\0\").decode())")
/usr/local/bin/mkbootimg --header_version 2 \
  --kernel out/arch/arm64/boot/Image \
  --ramdisk "${RAMDISK:-initrd/initrd-bitra-ecm.img}" \
  --dtb out/arch/arm64/boot/dts/vendor/21623/kona-v2.1.dtb \
  --cmdline "$STOCK_CMDLINE $EXTRA" \
  --base 0x00000000 --kernel_offset 0x00008000 --ramdisk_offset 0x01000000 \
  --tags_offset 0x00000100 --dtb_offset 0x01f00000 --pagesize 4096 \
  --os_version 12.0.0 --os_patch_level 2022-09-05 -o "$OUT"
python3 -I tools/avbtool.py add_hash_footer --image "$OUT" --partition_name boot --partition_size 100663296
