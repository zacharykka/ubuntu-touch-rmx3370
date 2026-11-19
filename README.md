# Ubuntu Touch on realme GT Neo2 (RMX3370, "bitra")

Ubuntu Touch 24.04-2.x on a Halium 11 GSI with a standalone 4.19 kernel, for
the realme GT Neo2 (SM8250-AC, OPLUS project 21619).

Status on 2026-11-19. The kernel now lives in the boot partition
(`fastboot flash boot`, see "Install"), so an ordinary reboot boots Ubuntu
Touch; RAM boot still works for testing kernels.

| Works | Not yet |
|---|---|
| boot to Lomiri, display | modem and calls |
| touch, with tap haptics | sensors |
| WiFi, IPv4 and IPv6 | AppArmor confinement (SELinux is the major LSM) |
| click apps launch (terminal, OpenStore, ...) | |
| mtp + adb on boot (usb-moded default mode) | |
| rear flash via the power menu Flashlight switch | |
| camera: preview, photo, video recording | |
| playback of audio and video (Gallery, mediaplayer) | |
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

## Install

Ubuntu Touch lives in `/userdata/ubuntu.img`, a 4 GiB ext4 image that the Halium
initrd loop-mounts as `/`. The kernel lives in the `boot` partition. The two are
independent, so a rootfs update never disturbs the kernel and vice versa.

Two consequences are easy to trip over:

- **Config is split between the image and the partition.** `/home` is a plain
  bind mount off `/dev/sda11`, so it is *not* inside `ubuntu.img` and survives
  an image swap. Per-user drop-ins in `~/.config/systemd/user/*.d/` and
  `~/.config/environment.d/` therefore override whatever the image ships.
  Remove them before validating an image, or you are testing the drop-ins.
- **The image can be swapped in place while Ubuntu Touch is running**, because
  the `phablet` account's sudo password is `0000`. This is much less fragile
  than the initrd path since it needs no ECM link: push the `.gz` to `/home`,
  `gunzip -c` it to `/userdata/ubuntu.img.new`, check its sha256, then `mv -f`
  it over `ubuntu.img`. The rename is atomic and the running loop0 keeps the old
  inode until the next boot, so the swap takes effect on reboot. Keep a copy as
  `ubuntu.img.bak-<date>` first.

The image file's own sha256 never matches the build output on a booted device.
Mounting rewrites the ext4 superblock (mount count, mount and write times), so
compare payload files instead: `dumpe2fs -h` shows `Mount count: 0` on the build
output and `1` after one boot.

### First install (erases userdata)

Userdata is reformatted as plain ext4, so stock Android loses its data. After
this, never pick "format data" or "factory reset" in the stock recovery, as that
erases `ubuntu.img`.

1. `fastboot boot images/boot-ut-debug.img`, then wait for the telnet shell at
   192.168.2.15 (CDC-ECM; the Mac gets an address in 192.168.2.0/24).
2. Copy your adb public key to `/tmp/adb_keys` on the phone, then push and run
   `tools/phone/setup-userdata.sh`. It checks the partition label and size
   before formatting `/dev/sda11`.
3. `tools/host/stream_push.py userspace/out/ubuntu.img.gz 5582 'gunzip -c > /mnt/ud/ubuntu.img' 1800`
4. `fastboot flash boot images/boot-ut.img`, or `fastboot boot` it once first.

### Flashing the kernel

`fastboot flash boot images/boot-ut.img` works, and is how this port is
installed as of 2026-11-19. Our boot images carry an AVB hash footer with
`Algorithm: NONE` (hash only, no signature) while `vbmeta.img` declares `boot`
as a chained partition expecting the OEM key, but unlocked ABL tolerates the
mismatch and boots from the partition.

`fastboot boot` bypasses the partition's AVB check entirely, so "the image
RAM-boots" is not by itself proof that it will boot from the partition. Check
that the footer is self-consistent instead:
`avbtool.py add_hash_footer --salt <the image's own salt>` reproduces the
image's digest. A rebuild with a fresh random salt produces a different digest
and proves nothing.

Only ever flash a normal image to `boot`. `boot-ut-debug.img` carries
`break=mountroot` and would sit in the initrd shell forever.

Flashing replaces the stock Android kernel, so Android no longer boots from this
partition; `fastboot flash boot` of the stock `boot.img` restores it.

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

**The camera preview crash is fixed, and it was not a camera-HAL bug.** It was a
missing BufferQueue in libhybris' own decoding service.

The crash was a SIGSEGV in `android::ConsumerBase::ConsumerBase()` in
`/android/system/lib64/libgui.so` (`+0x885b4`, `ldr x8,[x0]` with `x0 = 0`), a
virtual call on a NULL `IGraphicBufferConsumer`. The NULL comes from:

1. `DecodingService::getIGraphicBufferConsumer()` in
   `libmedia_compat_layer.so` (source `vendor/halium/libhybris/compat/media/`)
   reads the consumer member and writes it to the out-parameter, then
   **returns `OK` even when the member is NULL**.
2. That member is only ever populated by
   `DecodingService::createBufferQueue()` (producer at `this+0x28`, consumer at
   `this+0x30`).
3. **Nothing in this GSI calls `createBufferQueue()`** — the whole `.text` has
   zero call sites and `instantiate()` contains no branch to it. Upstream has
   the call; this binary does not.
4. `HybrisVideoSink` therefore hands a NULL consumer to
   `gl_consumer_create_by_id_with_igbc()`, which builds `GLConsumer(NULL)`, and
   the constructor above dereferences it.

The fix is `usr/lib/bitra/libbitra-camera-preview-fix.so` (source next to it),
preloaded through `/etc/environment`. It intercepts
`gl_consumer_create_by_id_with_igbc()` and, when the wrapper's consumer slot is
NULL, builds a real queue with libgui's exported
`android::BufferQueue::createBufferQueue()` and stores the consumer before
forwarding. `sp<T>` is a single pointer, so one 8-byte slot stands in for each
`sp<>`.

`media-hub` must **not** preload it. The shim builds one queue per call and
media-hub would share a single queue across every sink; the viewfinder and the
recorder then contend for it, `media-hub.service` dies with
`Main process exited, code=killed, status=11/SEGV`, and recording takes the
camera app down with it. Hence
`usr/lib/systemd/user/media-hub.service.d/50-bitra-preload.conf`, which sets
`LD_PRELOAD` to `libtls-padding.so` plus the media-hub AppArmor shim and leaves
the camera shim out. Photographing never hit the contention because it uses only
one stream.

Two dead ends, recorded so they are not retried:

- `libminisf.so` (fake SurfaceFlinger) is unrelated. It only provides a fake
  `ISurfaceComposer` and starts the binder thread pool; it has nothing to do
  with `IGraphicBufferConsumer`. Rebuilding Halium for it fixes nothing here.
- `android_camera_set_preview_texture()` is not on the crash path — it is never
  called in the app process.

The camera HAL and the kernel camera stack are healthy. A bare `Camera {}` with
no `VideoOutput` runs indefinitely with `cameraState=2` and a valid
`viewfinder.resolution` of 1920x1440, and the HAL does report
`preview-size-values`. The empty
`supportedViewfinderResolutions()` seen in the old crash logs was a consequence
of the client being torn down, not a cause.

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

Note that CamX's verbose output is stripped from this release vendor build and
`/data/vendor/camera/camxoverridesettings.txt` is **never read** — CamX only
looks at `/vendor/etc/camera/` and `./camxoverridesettings.txt`, both
unwritable (`/vendor` is erofs, `/` is read-only). Use logcat's Android-side
`Camera2-Parameters`, `Camera2Client` and `CamX` tags instead.

## Playback (media-hub)

Every media-hub session used to die with SIGSEGV, audio-only included, and
Gallery showed "Fail to connect with playback backend". The crash is not in the
video path.

SELinux is the major LSM here, and dbus-daemon fills a client's
`LinuxSecurityLabel` from `SO_PEERSEC` regardless of which LSM is primary, so
every connection on the session bus is reported as the SELinux context
`u:r:kernel:s0`. media-hub parses that as an AppArmor profile: it calls
`aa_splitcon()` and **discards the return value** (only the in-place truncation
matters), splits the label on `_`, and `Context::profile_name()` then reads
`app_id_parts[1]` with no bounds check. That is an out-of-bounds read of stale
heap, and `QString::append` on those bytes segfaults. The core dump's faulting
pointer `0x6e72656b3a723a75` is ASCII `u:r:kern`, which is what identifies it.

`usr/lib/bitra/libbitra-mediahub-apparmor-fix.so` interposes `aa_splitcon()`.
When the real function cannot parse the label and `aa_is_enabled()` reports
AppArmor is off, it rewrites the buffer in place to `unconfined` -- the truthful
answer with no policy loaded -- and media-hub takes its own unconfined path. On
a kernel where AppArmor is the major LSM the label parses and the shim changes
nothing, so it needs no cleanup after an LSM switch.

It is wired in by `usr/lib/systemd/user/media-hub.service.d/50-bitra-preload.conf`,
which also keeps the camera shim out. A shim that merely made `aa_splitcon()`
return a parsed result does nothing here: media-hub never looks at that return
value.

The out-of-bounds read in `profile_name()`, and mapping an unparseable label to
unconfined while AppArmor is off, both belong upstream in media-hub; the shim
only avoids the code path.

## Haptics

The AW8697 driver in this tree plays **every** vibration request as a
continuously looping sine wave. `activate_store()` calls
`aw8697_haptic_set_repeat_wav_seq(aw8697, AW8697_WAVEFORM_INDEX_SINE_CYCLE)`
unconditionally, and that helper programs `WAVSEQ1 = 9` together with
`WAVLOOP1[seq1] = AW8697_BIT_WAVLOOP_INIFINITELY` (`15 << 0` = `0x0f`). Nothing
in that path applies a brake or a decay envelope; the hrtimer simply issues a
bare `GO=0` when the duration expires.

That is fine for a long vibration and wrong for a tap. Touch feedback asks for
10 ms and got a 24.3 ms slice of overdriven looping sine, which reads as a hum
rather than a click. The `index` and `loop` sysfs nodes are no help: they are
overwritten by `activate_store()` before every play, so writing them changes
nothing.

`aw8697_vibrator_work_routine()` now splits on duration at
`AW8697_HAPTIC_SHORT_TAP_MS` (50 ms). At or below it the sequence is started the
same way the `haptic_audio` path does it -- `RAM_MODE`, waveform 8 (transient),
loop 0 -- so it plays once and self-stops, leaving the timer as a backstop.
Anything longer keeps the looping sine, so alarms and calls are unchanged. Touch
sends 10 ms and long vibrations send 500 ms, so the two cases are far apart and
the threshold is not delicate.

The check that matters is on the device: after a short request `seq1` must read
`0x08` with `seq1 loop: 0x00`, and after a long one `0x09` with `0x0f`.

**The SRAM firmware has to be in the rootfs.** The driver's
`request_firmware_nowait()` asks for `aw8697_haptic_170.bin` (device id 815,
`CRISP_STYLE` default), but the image shipped no `/usr/lib/firmware` directory
at all, so the request could not succeed and the motor played from
uninitialised SRAM. The file comes from the device's own
`/android/odm/firmware/` and is shipped by the overlay at
`usr/lib/firmware/aw8697_haptic_170.bin`. At boot `dmesg` should show
`crisp haptic bin name aw8697_haptic_170.bin`, `check sum pass` and
`fw update complete`.

Firmware alone does not fix the buzz -- it only initialises SRAM and un-gates
the `rtp` and `haptic_audio` write paths, which both check `ram_init`. The
waveform is fixed by the kernel change above. Do not reach for
`CONFIG_OPLUS_HAPTIC_OOS` to fix this: it rewrites the whole gain map and the
vmax limits, which is a much larger behaviour change than the problem needs.

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
  images without an AVB footer. `fastboot flash boot` works despite the AVB
  signature mismatch on an unlocked device; see "Flashing the kernel".
- The rootfs ships no `/usr/lib/firmware` directory, and the kernel uses the
  default search path, so any `request_firmware()` fails silently at boot. The
  AW8697 haptics firmware is shipped by the overlay for this reason.
- `aw8697`'s `index` and `loop` sysfs nodes look settable but are overwritten by
  `activate_store()` before every play. Changing the touch waveform means
  changing the kernel, not the nodes.
- `media-hub` must not preload the camera-preview shim. It builds one
  BufferQueue per call and media-hub would share a single queue across sinks, so
  the viewfinder and recorder contend and media-hub dies with
  `status=11/SEGV`, taking recording down with it.
