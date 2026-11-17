#!/usr/bin/env python3
"""Node-path diff of two DTBs, restricted to nodes that have a 'compatible' and
are not disabled; also reports which of the stock-bound devices are absent."""
import subprocess
import sys


def walk(dtb):
    out = subprocess.run(['fdtget', '-l', dtb, '/'], capture_output=True, text=True)
    todo = ['/' + n for n in out.stdout.split()]
    nodes = {}
    while todo:
        p = todo.pop()
        props = subprocess.run(['fdtget', '-p', dtb, p], capture_output=True, text=True).stdout.split()
        if 'compatible' in props:
            comp = subprocess.run(['fdtget', dtb, p, 'compatible'], capture_output=True, text=True).stdout.strip()
            status = ''
            if 'status' in props:
                status = subprocess.run(['fdtget', dtb, p, 'status'], capture_output=True, text=True).stdout.strip()
            nodes[p] = (comp, status)
        kids = subprocess.run(['fdtget', '-l', dtb, p], capture_output=True, text=True).stdout.split()
        todo.extend(f'{p}/{k}' for k in kids)
    return nodes


def enabled(n):
    return {p: v for p, v in n.items() if v[1] in ('', 'okay', 'ok')}


def main(ours, live, bound):
    o, l = enabled(walk(ours)), enabled(walk(live))
    bound_nodes = set()
    for line in open(bound, errors='replace'):
        parts = line.rstrip('\n').split('|')
        if len(parts) >= 4 and parts[3]:
            bound_nodes.add(parts[3])
    print(f'enabled compatible nodes: ours={len(o)} live={len(l)}')
    miss_bound = sorted(p for p in bound_nodes if p in l and p not in o)
    print(f'\nnodes BOUND to a driver on stock but absent/disabled in ours: {len(miss_bound)}')
    for p in miss_bound:
        print(f'   {p}  [{l[p][0]}]')
    only_live = sorted(set(l) - set(o) - set(miss_bound))
    print(f'\nother enabled nodes only in live (not bound on stock): {len(only_live)}')
    for p in only_live[:40]:
        print(f'   {p}  [{l[p][0]}]')
    only_ours = sorted(set(o) - set(l))
    print(f'\nenabled nodes only in ours: {len(only_ours)}')
    for p in only_ours[:40]:
        print(f'   {p}  [{o[p][0]}]')


if __name__ == '__main__':
    main(*sys.argv[1:4])
