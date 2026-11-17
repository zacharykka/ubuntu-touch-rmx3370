#!/usr/bin/env python3
"""Pull a file (or command output) from the phone: phone connects to us with nc and sends it."""
import re
import socket
import subprocess
import sys
import threading

remote_cmd, dst, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
mac_ip = re.search(r'inet (192\.168\.2\.\d+)',
                   subprocess.run(['ifconfig'], capture_output=True, text=True).stdout).group(1)
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('0.0.0.0', port))
srv.listen(1)
srv.settimeout(60)
buf = bytearray()


def recv():
    conn, _ = srv.accept()
    conn.settimeout(60)
    while True:
        d = conn.recv(1 << 16)
        if not d:
            break
        buf.extend(d)
    conn.close()


t = threading.Thread(target=recv)
t.start()
subprocess.run(['python3', '-I', '/tmp/rmx3370-scout/tn.py',
                f'({remote_cmd}) | nc {mac_ip} {port}', '90'], capture_output=True)
t.join(timeout=95)
srv.close()
open(dst, 'wb').write(buf)
print(f'{dst}: {len(buf)} bytes')
