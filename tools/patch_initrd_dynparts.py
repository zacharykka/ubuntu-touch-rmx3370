#!/usr/bin/env python3
"""Halium initrd: do not map the OPLUS my_* logical partitions from super."""
import sys

p = sys.argv[1]
s = open(p).read()
old = '\t\t/sbin/parse-android-dynparts /dev/disk/by-partlabel/super | sh\n'
new = ('\t\t# bitra: skip the OPLUS my_* logical partitions. Ubuntu Touch does not use\n'
       '\t\t# them, and udev probing ten extra dm devices slows boot considerably.\n'
       '\t\t/sbin/parse-android-dynparts /dev/disk/by-partlabel/super | \\\n'
       '\t\t\tawk \'/^dmsetup create /{skip=($3 ~ /^my_/)} !skip{print} /^EOF$/{skip=0}\' | sh\n')
if s.count(old) != 1:
    sys.exit('anchor not found exactly once')
open(p, 'w').write(s.replace(old, new))
print('patched')
