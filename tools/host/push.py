#!/usr/bin/env python3
"""Push a file to the phone: serve it once on a TCP port, have the phone fetch it with nc."""
import socket
import subprocess
import sys
import threading
import re

src, dst, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = open(src, 'rb').read()
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('0.0.0.0', port))
srv.listen(1)
srv.settimeout(30)


def serve():
    conn, _ = srv.accept()
    conn.sendall(data)
    conn.shutdown(socket.SHUT_WR)
    conn.close()


t = threading.Thread(target=serve)
t.start()
import subprocess as _sp
mac_ip = re.search(r'inet (192\.168\.2\.\d+)', _sp.run(['ifconfig'], capture_output=True, text=True).stdout).group(1)
cmd = f'nc {mac_ip} {port} > {dst}; chmod 755 {dst}; sha256sum {dst}'
out = subprocess.run(['python3', '-I', '/tmp/rmx3370-scout/tn.py', cmd, '30'],
                     capture_output=True, text=True).stdout
t.join(timeout=35)
srv.close()
import hashlib
print('local ', hashlib.sha256(data).hexdigest()[:16], len(data))
print('remote', [l for l in out.splitlines() if dst in l and len(l) > 64][-1:])
