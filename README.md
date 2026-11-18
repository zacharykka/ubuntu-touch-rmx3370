# Ubuntu Touch on realme GT Neo2 (RMX3370, "bitra")

Ubuntu Touch 24.04-2.x on a Halium 11 GSI with a standalone 4.19 kernel, for
the realme GT Neo2 (SM8250-AC, OPLUS project 21619).

Status on 2026-11-17. Everything is tested by RAM boot (`fastboot boot`);
nothing is flashed.

| Works | Not yet |
|---|---|
| boot to Lomiri, display | audio, modem and calls, sensors |
| touch | camera and flash from the camera app |
| WiFi, IPv4 and IPv6 | AppArmor confinement (SELinux is the major LSM) |
| click apps launch (terminal, OpenStore, ...) | |
| mtp + adb on boot (usb-moded default mode) | |
| rear flash via the power menu Flashlight switch | |
| adb survives USB drops (see below) | |

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

## Camera and flashlight

The rear flash works from the power menu's **Flashlight** switch. That path does
not go through the camera at all: `ayatana-indicator-power` probes
`/sys/class/leds/led:torch_0` plus `led:switch_0` by itself and drives them in
the two steps `qpnp-flash-led-v2` needs (a current on the torch node, then 1 on
the paired switch, whose `qcom,led-mask = 0x1` enables fnode 0). The only thing
missing was permission: the kernel exposes those `brightness` files as
root:root 0644, so the indicator's `fopen(..., "w")` got EACCES and
`toggle_flashlight_action_qcom()` returned 0 *silently* — the switch looked
dead and nothing was logged. `bitra-torch-perms.service` chgrp/chmods the two
nodes to `plugdev` 0660 (phablet is already in that group).

Do not add `FlashlightSysfsPath` to `/etc/deviceinfo/devices/kona.yaml` without
a matching `FlashlightSwitchPath`: a path without a switch drops the backend to
SIMPLE, which writes a single value and never powers the LED.

**The camera app still crashes, and it is not a camera-HAL bug.** The chain,
confirmed by replaying the real launcher environment (77 variables) and reading
the resulting backtrace:

1. `ViewFinderView.qml` attaches `VideoOutput { source: camera }`, which asks
   for a video node as soon as the viewfinder starts.
2. `camera.supportedViewfinderResolutions()` returns an empty list — the QML
   logs `updateViewfinderResolution: viewfinder resolutions is not known yet.`
   on every pass (`ViewFinderOverlay.qml:161`).
3. That list comes from `libcamera.so.1` (the hybris camera shim) calling
   `android_camera_enumerate_supported_preview_sizes`, which gets nothing back
   from CamX.
4. This device has exactly one video-node factory,
   `qt5/plugins/video/videonode/libshadervideonode.so`; `libhaliumqsgcontext.so`
   is a scene-graph *context*, not a video-node factory, so there is no
   alternative to fall back to.
5. `ShaderVideoNodePlugin::createNode()` is handed the resulting invalid format
   and segfaults. That is the `Segmentation fault` after
   `virtual QSGVideoNode* ShaderVideoNodePlugin::createNode(...)`.

Upstream of all this, CamX does open the camera: `CameraService::connect
(hybris, camera 0)` then `Camera 0: Opened`, and 110 ms later
`notifyError: Error condition 0` (`CAMERA3_MSG_ERROR_DEVICE`) followed by
`CamX flush()`. So open() succeeds and the first configure fails inside CamX,
which is why no preview size ever reaches Qt.

Camera 0 is the **s5kgw1** (64MP Samsung GW1), not the imx471: ODM
`CameraHWConfiguration.config`, `camera_engmode.xml` and the runtime metadata
(activeArray 4608x3456, 7.3728x5.5296 mm) all agree. In the kernel the chip-id
dispatch is `0x971 = s5kgw1`, `0x471 = imx471`, `0x4608 = hi846`,
`0x2b = ov02b`, so probe slot 0 is the main wide sensor and the mapping is
self-consistent. Reason about camera 0 against s5kgw1.

Do **not** diagnose this by exec'ing the binary with a hand-built environment:
without `GLIBC_TUNABLES=glibc.rtld.optional_static_tls=4096` libhybris dies with
`cannot allocate memory in static TLS block`, and a bare launch aborts in
`ContentHub`/`libertine` (`liblibertine` reports with `g_error()`), which is a
completely different crash. `/userdata/dbg/cam-real.sh` replays the real
environment and reproduces the real fault.

Useful knobs, all verified to work: the CamX log masks are
`persist.camera.logVerboseMask` / `logInfoMask` / `logWarningMask` (unprefixed —
the `persist.vendor.camera.*` spelling is read by nothing), and CHI has its own
`persist.camera.OverrideLogLevels`. They are read at process start, so the
camera provider must be restarted. Capture immediately afterwards: the logcat
ring buffers are 256 KiB each. Note that
`setprop ctl.restart vendor.camera-provider-2-4` can leave the provider stuck in
`stopping` with the process still alive; `kill -9` the provider and init starts
a fresh one.

## USB drops and adb

adb goes offline in two shapes, and they need different fixes.

*Shape B — the gadget leaves the bus.* The phone disappears from the host's USB
bus. `bitra-usb-recover.timer` checks every 30 s and, when
`power_supply/usb/present` is 1 while the gadget is no longer attached to the
UDC across two consecutive samples, restarts usb-moded. It stays quiet for the
first 90 s after boot and at most once per 120 s. Verified by unbinding the
gadget by hand: the timer noticed and the phone came back on the bus.

*Shape A — the gadget is fine, the transport is dead.* adbd still holds its
endpoints, the UDC says `configured`, and everything on the phone looks healthy,
while the host keeps listing the device as `offline`. The device cannot see
this: it is the host's adb server that has stalled. `adb kill-server` clears it;
`tools/host/adb-watch.sh` does that automatically. It is deliberately not
installed as a login item — run it when you want it. Do **not** use a bare
`systemctl restart adbd` to recover: that de-enumerated the phone from the bus
entirely in testing.

adbd also used to die of SIGSEGV. Both crashes in the boot where it happened
were preceded by `dwc3 a600000.dwc3: request ... was not queued to ep0out` from
the `adbd auth` thread, and only boots that exercised host-key authentication
showed any. The port runs with `ADBD_SECURE=0`
(`adbd.service.d/60-bitra-no-secure.conf`); the same disturbance is then handled
by the UsbFfs worker thread and adbd survives it. Verification adds nothing here
— `/data/misc/adb/adb_keys` already holds the host key.

The underlying reason the gadget keeps being re-composed is still unknown; both
mechanisms above recover from it rather than prevent it.

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
