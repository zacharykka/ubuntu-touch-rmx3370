# Build environment for the bitra Ubuntu Touch kernel
TC=/root/ut-work/toolchains
export PATH=$TC/clang-r416183b/bin:$TC/gcc-aarch64-4.9/bin:$TC/gcc-arm-4.9/bin:/usr/sbin:/usr/bin:/sbin:/bin
export ARCH=arm64 SUBARCH=arm64
KSRC=/root/ut-work/port-bitra/kernel-src
KOUT=${KOUT:-/root/ut-work/port-bitra/out}
MK="make -C $KSRC O=$KOUT ARCH=arm64 CC=clang CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-android- CROSS_COMPILE_ARM32=arm-linux-androideabi- LLVM_IAS=1 NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump STRIP=llvm-strip"
