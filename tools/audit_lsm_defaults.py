#!/usr/bin/env python3
"""Compare each LSM_HOOK() default in lsm_hook_defs.h with the initial value
security.c passes to call_int_hook() for the same hook. With the BPF LSM, the
default is what bpf_lsm_<hook>() returns when no BPF program is attached."""
import re
import sys

root = sys.argv[1]
defs = {}
src = open(f'{root}/include/linux/lsm_hook_defs.h').read()
for m in re.finditer(r'LSM_HOOK\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([a-z0-9_]+)\s*,', src):
    defs[m.group(3)] = m.group(2).strip()
sec = open(f'{root}/security/security.c').read()
sites = re.findall(r'call_int_hook\(\s*([a-z0-9_]+)\s*,\s*([^,]+?)\s*,', sec)
print(f'hooks defined: {len(defs)}  call_int_hook sites: {len(sites)}')
seen = set()
for hook, irc in sites:
    irc = irc.strip()
    d = defs.get(hook)
    if d is not None and d != irc and (hook, irc) not in seen:
        seen.add((hook, irc))
        print(f'MISMATCH {hook}: LSM_HOOK default={d}  call_int_hook initial={irc}')
