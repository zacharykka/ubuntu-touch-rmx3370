#!/usr/bin/env python3
"""Verify a boot image v2: compare header fields with the stock image and check
that each section round-trips byte-for-byte to the intended input file."""
import hashlib
import struct
import sys


def parse(path):
    d = open(path, 'rb').read()
    if d[:8] != b'ANDROID!':
        sys.exit(f'{path}: bad magic')
    (ks, ka, rs, ra, ss, sa, ta, ps, hv, osv) = struct.unpack('<10I', d[8:48])
    off = 64 + 512 + 32 + 1024
    rdtbo_sz, rdtbo_off, hdr_sz = struct.unpack('<IQI', d[off:off + 16])
    dtb_sz, dtb_addr = struct.unpack('<IQ', d[off + 16:off + 28])
    h = dict(kernel_size=ks, kernel_addr=ka, ramdisk_size=rs, ramdisk_addr=ra,
             second_size=ss, second_addr=sa, tags_addr=ta, page_size=ps,
             header_version=hv, os_version=osv, recovery_dtbo_size=rdtbo_sz,
             header_size=hdr_sz, dtb_size=dtb_sz, dtb_addr=dtb_addr,
             name=d[48:64].rstrip(b'\0'), cmdline=d[64:576].rstrip(b'\0').decode(),
             extra_cmdline=d[608:1632].rstrip(b'\0').decode())
    al = lambda x: (x + ps - 1) // ps * ps
    k0 = ps
    r0 = k0 + al(ks)
    s0 = r0 + al(rs)
    o0 = s0 + al(ss)
    t0 = o0 + al(rdtbo_sz)
    secs = dict(kernel=d[k0:k0 + ks], ramdisk=d[r0:r0 + rs], dtb=d[t0:t0 + dtb_sz])
    h['payload_end'] = t0 + al(dtb_sz)
    return h, secs, len(d)


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main(img, stock, kernel, ramdisk, dtb, suffix=" console=tty0"):
    h, secs, total = parse(img)
    hs, _, _ = parse(stock)
    ok = True
    print('header field          ours                stock')
    for k in ('header_version', 'page_size', 'kernel_addr', 'ramdisk_addr', 'second_addr',
              'tags_addr', 'dtb_addr', 'os_version', 'header_size', 'second_size',
              'recovery_dtbo_size', 'name', 'extra_cmdline'):
        same = h[k] == hs[k]
        ok &= same
        print(f"{'  ' if same else '!!'}{k:<20} {str(h[k]):<19} {hs[k]}")
    exp_cmd = hs["cmdline"] + suffix
    same = h['cmdline'] == exp_cmd
    ok &= same
    print(f"{'  ' if same else '!!'}cmdline == stock + {suffix!r}: {same}")
    for name, path in (('kernel', kernel), ('ramdisk', ramdisk), ('dtb', dtb)):
        want = open(path, 'rb').read()
        same = secs[name] == want
        ok &= same
        print(f"{'  ' if same else '!!'}{name:<8} {len(secs[name]):>10} B  sha256 {sha(secs[name])}  == input: {same}")
    print(f"  payload end {h['payload_end']} B, image file {total} B, partition 100663296 B, "
          f"headroom {100663296 - h['payload_end']} B")
    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:7]))
