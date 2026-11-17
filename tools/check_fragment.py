#!/usr/bin/env python3
"""Verify that every directive of a Kconfig fragment took effect in a .config."""
import re
import sys

DIRECTIVE = re.compile(r'^(# )?CONFIG_([A-Za-z0-9_]+)[= ]')


def parse(path):
    vals = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.rstrip('\n')
        m = re.match(r'^CONFIG_([A-Za-z0-9_]+)=(.*)$', line)
        if m:
            vals[m.group(1)] = m.group(2)
            continue
        m = re.match(r'^# CONFIG_([A-Za-z0-9_]+) is not set$', line)
        if m:
            vals[m.group(1)] = 'n'
    return vals


def main(fragment, dotconfig):
    want = parse(fragment)
    have = parse(dotconfig)
    bad = 0
    for sym, val in sorted(want.items()):
        got = have.get(sym, 'n')  # absent from .config == not set
        ok = (got == val)
        if not ok:
            bad += 1
        print(f"{'OK  ' if ok else 'FAIL'} CONFIG_{sym}: want={val} got={got}")
    print(f"\n{len(want) - bad}/{len(want)} directives satisfied")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
