#!/usr/bin/env python3
"""List symbols enabled in the stock config but not in ours, restricted to symbols
that exist in this kernel tree, grouped by the Kconfig file that defines them."""
import os
import re
import sys
from collections import defaultdict


def parse(path):
    vals = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^CONFIG_([A-Za-z0-9_]+)=(.*)$', line.strip())
        if m:
            vals[m.group(1)] = m.group(2)
    return vals


def kconfig_index(root):
    where = {}
    rx = re.compile(r'^\s*(?:menu)?config\s+([A-Za-z0-9_]+)\s*$')
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('.git', 'Documentation')]
        for fn in filenames:
            if not fn.startswith('Kconfig'):
                continue
            p = os.path.join(dirpath, fn)
            for line in open(p, encoding='utf-8', errors='replace'):
                m = rx.match(line)
                if m:
                    where.setdefault(m.group(1), os.path.relpath(p, root))
    return where


def main(stock, ours, ksrc):
    s, o, idx = parse(stock), parse(ours), kconfig_index(ksrc)
    groups = defaultdict(list)
    missing_tree = 0
    for sym, val in s.items():
        if val not in ('y', 'm'):
            continue
        if sym in o and o[sym] in ('y', 'm'):
            continue
        if sym not in idx:
            missing_tree += 1
            continue
        groups[os.path.dirname(idx[sym])].append(f"{sym}={val}")
    total = sum(len(v) for v in groups.values())
    print(f"stock y/m symbols not enabled in ours (and defined in this tree): {total}")
    print(f"stock y/m symbols with no Kconfig definition in this tree: {missing_tree}\n")
    for d in sorted(groups):
        print(f"[{d}] " + " ".join(sorted(groups[d])))


if __name__ == '__main__':
    main(*sys.argv[1:4])
