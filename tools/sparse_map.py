#!/usr/bin/env python3
"""List the byte ranges of a raw partition that an Android sparse image actually carries."""
import struct
import sys

f = open(sys.argv[1], 'rb')
magic, major, minor, fhs, chs, blksz, total_blks, total_chunks, csum = struct.unpack('<IHHHHIIII', f.read(28))
assert magic == 0xED26FF3A, hex(magic)
f.seek(fhs)
blk = 0
ranges = []
for _ in range(total_chunks):
    ctype, _r, csize, ctotal = struct.unpack('<HHII', f.read(12))
    if ctype in (0xCAC1, 0xCAC2):  # RAW, FILL
        if ranges and ranges[-1][1] == blk:
            ranges[-1][1] = blk + csize
        else:
            ranges.append([blk, blk + csize])
    f.seek(ctotal - chs, 1)
    blk += csize
print(f'block size {blksz}, total {total_blks * blksz / 2**20:.1f} MiB, chunks {total_chunks}')
for a, b in ranges:
    print(f'  data: sectors {a * blksz // 512:>10} .. {b * blksz // 512:>10}   ({a * blksz / 2**20:9.1f} .. {b * blksz / 2**20:9.1f} MiB)')
