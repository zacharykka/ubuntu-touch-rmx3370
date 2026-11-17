#!/usr/bin/env python3
"""Deterministic node diff: parse `dtc -O dts` text, then check that every device
node bound to a driver on stock is present and enabled in our merged tree."""
import re
import subprocess
import sys
from collections import Counter

NODE = re.compile(r'^\s*(?:[A-Za-z0-9_]+:\s*)*([^\s{}=;]+)\s*\{\s*$')
PROP = re.compile(r'^\s*([A-Za-z0-9,._+#?-]+)\s*=\s*(.*);\s*$')


def nodes(dtb):
    dts = subprocess.run(['dtc', '-q', '-I', 'dtb', '-O', 'dts', dtb],
                         capture_output=True, text=True, check=True).stdout
    stack, out = [], {}
    for line in dts.splitlines():
        m = NODE.match(line)
        if m:
            name = m.group(1)
            stack.append(name)
            path = '/' if name == '/' else '/' + '/'.join(stack[1:])
            out[path] = {}
            continue
        if line.strip() == '};':
            stack.pop()
            continue
        m = PROP.match(line)
        if m and stack:
            path = '/' if len(stack) == 1 else '/' + '/'.join(stack[1:])
            out[path][m.group(1)] = m.group(2)
    return out


def enabled(props):
    st = props.get('status', '"okay"').strip('"')
    return st in ('okay', 'ok')


def main(ours, live, bound):
    o, l = nodes(ours), nodes(live)
    print(f'parsed nodes: ours={len(o)} live={len(l)}')
    bound_nodes = []
    for line in open(bound, errors='replace'):
        parts = line.rstrip('\n').split('|')
        if len(parts) >= 4 and parts[3]:
            bound_nodes.append((parts[3], parts[2]))
    uniq = sorted(set(bound_nodes))
    absent, disabled = [], []
    for path, drv in uniq:
        if path not in o:
            absent.append((path, drv))
        elif not enabled(o[path]):
            disabled.append((path, drv))
    print(f'stock-bound device nodes: {len(uniq)}  present+enabled in ours: '
          f'{len(uniq) - len(absent) - len(disabled)}  absent: {len(absent)}  disabled: {len(disabled)}')
    debug = re.compile(r'(cti|funnel|tpda|tpdm|tmc|replicator|stm|etm|hwevent|csr|dummy_sink|tgu)')
    for title, items in (('ABSENT', absent), ('DISABLED', disabled)):
        nondebug = [x for x in items if not debug.search(x[0])]
        kinds = Counter(debug.search(x[0]).group(1) for x in items if debug.search(x[0]))
        print(f'\n{title}: coresight/debug={sum(kinds.values())} {dict(kinds)}  other={len(nondebug)}')
        for path, drv in nondebug:
            print(f'   {path}  (stock driver: {drv})')


if __name__ == '__main__':
    main(*sys.argv[1:4])
