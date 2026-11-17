# Ubuntu Touch on realme GT Neo2 (RMX3370, "bitra")

Ubuntu Touch 24.04-2.x on a Halium 11 GSI with a standalone 4.19 kernel, for
the realme GT Neo2 (SM8250-AC, OPLUS project 21619).

Status on 2026-11-17. Everything is tested by RAM boot (`fastboot boot`);
nothing is flashed.

| Works | Not yet |
|---|---|
| boot to Lomiri, display | audio, modem and calls, sensors |
| touch | USB networking and adb while Ubuntu Touch runs |
| WiFi, IPv4 and IPv6 | AppArmor confinement (SELinux is the major LSM) |
| click apps launch (terminal, camera, OpenStore, ...) | |

## Security model

This device trades the normal Ubuntu Touch application sandbox for a working
display stack, and callers should understand what that means.

- **AppArmor is off.** In this 4.19 tree SELinux and AppArmor are both
  exclusive LSMs, so only the first one in `CONFIG_LSM` initialises. SELinux
  has to win (the display composer needs selinuxfs, see the note below), which
  leaves AppArmor uninitialised. Ubuntu Touch's per-click-app confinement is
  built on AppArmor, so that sandbox does not exist here.
- **SELinux does not confine the Ubuntu side.** It is the major LSM only so
  that the Android container's `vndservicemanager` can register. No policy is
  loaded for the Ubuntu userspace and the kernel runs SELinux permissive, so it
  does not restrict Ubuntu Touch apps either.
- **What is left is standard Unix DAC.** Apps run as the `phablet` user under
  ordinary file permissions, like a normal desktop Linux session, with no
  mobile-style per-app isolation. Treat OpenStore / third-party clicks
  accordingly.
- **Consequence for launching apps.** `lomiri-app-launch` starts every click
  app through its systemd exec-tool, which runs `aa-exec -p <profile> -- <app>`.
  With AppArmor absent `aa-exec` aborts with "AppArmor interface not available"
  and the app never execs, so terminal, OpenStore and the rest fail to launch.
  The overlay replaces `/usr/bin/aa-exec` with a shim: when AppArmor is
  unavailable it drops the `-p <profile>` / `-n <ns>` options and execs the app
  unconfined (all other click environment is still set up); when AppArmor is
  enabled it defers to the original binary, kept as `/usr/bin/aa-exec.real`
  (saved at build time by `tools/make_ut_image.sh`, so the GPL binary is not in
  this repo). The overlay also patches `/usr/bin/aa-exec-click`, which the
  `desktop-hook` launch path uses, the same way. On a kernel with AppArmor
  enabled both are no-ops and apps are confined as before. Restoring the sandbox
  would require either LSM stacking in the kernel or SELinux policy for the
  Ubuntu side; the `apparmor-major-lsm` branch tracks the first of those.

## Layout

| Path | Content |
|---|---|
| `env.sh` | toolchain paths and the kernel `make` command (`$MK`) |
| `patches/` | kernel patch series, see "Build" step 2 |
| `device/rootfs-overlay/` | files copied over the Ubuntu Touch rootfs |
| `tools/` | build, boot image and analysis scripts (each starts with a comment saying what it does) |
| `tools/host/` | helpers that run on the Mac for the debug shell |
| `tools/phone/` | scripts and units that run on the phone |

Not tracked: `kernel-src/` (a separate git repository), and everything that
`tools/fetch_inputs.sh` downloads or the build produces (`out/`, `initrd/`,
`images/`, `userspace/`).

## Build

All commands run on the build machine from this directory.

1. Inputs: `tools/fetch_inputs.sh` fetches the toolchains, the UT rootfs, the
   Halium 11 GSI and the Halium initrd, and checks them against
   `tools/inputs.sha256`. A dump of the stock boot partition must also be at
   `/root/ut-work/ref/boot.img`; only its kernel cmdline is reused.
2. Kernel: branch `ut-bitra` of
   [ubuntu-touch-rmx3370-kernel-src](https://github.com/zacharykka/ubuntu-touch-rmx3370-kernel-src),
   a fork of `yassshhhhh15/android_kernel_realme_sm8250`.

   ```sh
   git clone -b ut-bitra https://github.com/zacharykka/ubuntu-touch-rmx3370-kernel-src kernel-src
   tools/build_kernel.sh
   ```

   `patches/` holds the same changes as a series on top of `6367b2e38fca`
   (the base commit, kept on that branch; upstream `cip-4.19.y-oos16` has
   since rewritten its last three commits). After changing the kernel,
   re-export it with
   `git -C kernel-src format-patch -o ../patches 6367b2e38fca..HEAD`.

   The config is `vendor/kona-perf_defconfig` plus
   `arch/arm64/configs/vendor/halium.config` (do not use `kona_defconfig`, see
   the script).
3. Initrd: `tools/make_initrd.sh`
4. Boot images:

   ```sh
   RAMDISK=initrd/initrd-bitra-ut.img tools/make_test_boot.sh images/boot-ut.img "console=tty0 printk.devkmsg=on"
   RAMDISK=initrd/initrd-bitra-ut.img tools/make_test_boot.sh images/boot-ut-debug.img "console=tty0 break=mountroot"
   ```

   `console=tty0` is required. Without it run-init fails with
   `opening console: No such device`. The script adds the AVB hash footer that
   the bootloader insists on.
5. Rootfs: `tools/make_ut_image.sh` writes `userspace/out/ubuntu.img` and
   `ubuntu.img.gz`.

## Install (erases userdata)

From the Mac, with the images and `ubuntu.img.gz` copied over.

Ubuntu Touch lives in `/userdata/ubuntu.img`. Userdata is reformatted as plain
ext4, so stock Android loses its data. After this, never pick "format data" or
"factory reset" in the stock recovery, as that erases `ubuntu.img`.

1. `fastboot boot images/boot-ut-debug.img`, then wait for the telnet shell at
   192.168.2.15 (CDC-ECM; the Mac gets an address in 192.168.2.0/24).
2. Copy your adb public key to `/tmp/adb_keys` on the phone, then push and run
   `tools/phone/setup-userdata.sh`. It checks the partition label and size
   before formatting `/dev/sda11`.
3. `tools/host/stream_push.py userspace/out/ubuntu.img.gz 5582 'gunzip -c > /mnt/ud/ubuntu.img' 1800`
4. `fastboot boot images/boot-ut.img`

## Debugging loop

- `boot-ut-debug.img` stops in the initrd's busybox shell instead of starting
  Ubuntu Touch. From the Mac: `tools/host/tn.py 'command' [timeout]`,
  `push.py`, `pull.py`. Mount userdata with `mount -t ext4 /dev/sda11 /mnt/ud`.
- To inspect a running Ubuntu Touch, install `tools/phone/bitra-diag.service`
  (instructions are in the file), write the payload to `/userdata/diag.sh` and
  end it with `/userdata/rebootbl`. RAM-boot `boot-ut.img`: the phone runs the
  payload and returns to fastboot by itself. Then read the results from the
  debug shell.
- `rebootbl` reboots into fastboot:
  `aarch64-linux-gnu-gcc -O2 -static -o tools/mnttest/rebootbl tools/mnttest/rebootbl.c`
- Logs of the last Ubuntu Touch boot: `/userdata/bitra-dmesg.log` (kernel
  log plus forwarded journal entries) and `/userdata/android-logcat.log`
  (container logcat; the boot before is kept as `.old`).
- To check which files on the phone differ from a build, run
  `tools/rootfs_manifest.sh` on the mounted `ubuntu.img` on both sides and
  diff the output (it works with busybox).

## Things that are easy to get wrong

- SELinux must be the major LSM, and userspace must load the vendor policy
  (`bitra-selinux-policy.service`). Without that, vndservicemanager cannot
  register, the display composer never starts and the screen stays black.
- `/etc/systemd/system` is a "synced" writable path: Ubuntu Touch copies it to
  `/userdata/system-data` once and never updates existing files there. Units
  therefore ship in `/usr/lib/systemd/system`. A stale copy with the same name
  in `/userdata/system-data/etc/systemd/system` overrides them.
- The qcacld WLAN driver does nothing until "ON" is written to `/dev/wlan`
  (`bitra-wlan.service`).
- Click apps launch unconfined because AppArmor is not initialised; the overlay
  replaces `/usr/bin/aa-exec` (and `/usr/bin/aa-exec-click`) with a shim that
  drops `-p <profile>` in that case, keeping the original as `aa-exec.real`. See
  the "Security model" section.
- The vendor `init.qcom.usb.rc` would take over the USB controller. The lxc
  config binds an empty file over it (see `tools/make_ut_image.sh`).
- The bootloader picks the DTB by `oplus,dtsi_no` = 21619 and refuses boot
  images without an AVB footer.
