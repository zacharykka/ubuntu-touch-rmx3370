#!/usr/bin/env python3
"""Compare /reserved-memory children (name, reg, size, flags) of two DTBs."""
import subprocess
import sys


def fdt_list(dtb, path):
    out = subprocess.run(['fdtget', '-l', dtb, path], capture_output=True, text=True)
    return out.stdout.split()


def fdt_props(dtb, path):
    out = subprocess.run(['fdtget', '-p', dtb, path], capture_output=True, text=True)
    return out.stdout.split()


def fdt_get(dtb, path, prop):
    out = subprocess.run(['fdtget', '-t', 'x', dtb, path, prop], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def regions(dtb):
    res = {}
    for name in fdt_list(dtb, '/reserved-memory'):
        p = f'/reserved-memory/{name}'
        props = fdt_props(dtb, p)
        res[name] = {
            'reg': fdt_get(dtb, p, 'reg'),
            'size': fdt_get(dtb, p, 'size'),
            'flags': ' '.join(x for x in ('no-map', 'reusable') if x in props),
        }
    return res


def main(a, b):
    ra, rb = regions(a), regions(b)
    names = sorted(set(ra) | set(rb))
    same = diff = 0
    for n in names:
        x, y = ra.get(n), rb.get(n)
        if x == y:
            same += 1
            continue
        diff += 1
        print(f'DIFF {n}\n   ours : {x}\n   stock: {y}')
    print(f'\nregions identical: {same}, differing/missing: {diff}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
