#!/usr/bin/env python3
"""Run one shell command on the Halium initrd telnet shell (busybox telnetd, no auth)."""
import socket
import sys
import time

HOST, PORT = '192.168.2.15', 23
cmd = sys.argv[1]
timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
MARK = '__CMD_DONE_7f3a__'

s = socket.create_connection((HOST, PORT), timeout=10)
s.settimeout(0.5)


def drain(buf):
    """Read available bytes, answering telnet IAC negotiation with refusals."""
    out = bytearray()
    try:
        data = s.recv(65536)
    except socket.timeout:
        return out, True
    if not data:
        return out, False
    i = 0
    while i < len(data):
        b = data[i]
        if b == 255 and i + 2 < len(data):  # IAC
            verb, opt = data[i + 1], data[i + 2]
            if verb in (251, 252):  # WILL/WONT -> DONT
                s.sendall(bytes([255, 254, opt]))
            elif verb in (253, 254):  # DO/DONT -> WONT
                s.sendall(bytes([255, 252, opt]))
            i += 3
            continue
        out.append(b)
        i += 1
    return out, True


acc = bytearray()
t_end = time.time() + 3
while time.time() < t_end:  # swallow banner/prompt
    d, alive = drain(acc)
    acc += d
s.sendall(("stty -echo 2>/dev/null; " + cmd + "; echo; echo " + MARK + "\n").encode())
acc = bytearray()
t_end = time.time() + timeout
while time.time() < t_end:
    d, alive = drain(acc)
    acc += d
    if acc.count(MARK.encode()) >= 1 and acc.rstrip().endswith(b'#') or acc.count(MARK.encode()) >= 2:
        break
    if not alive:
        break
s.close()
text = acc.decode('utf-8', 'replace').replace('\r', '')
# strip everything up to and including the echoed command line, if echoed
if MARK in text:
    text = text[:text.rfind(MARK)]
sys.stdout.write(text)
