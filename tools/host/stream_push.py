#!/usr/bin/env python3
"""Stream a large file to the phone over the ECM link and run a pipeline on it.
usage: stream_push.py FILE PORT 'remote shell pipeline reading stdin' TIMEOUT"""
import os
import re
import socket
import subprocess
import sys
import threading
import time

path, port, pipeline, timeout = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
mac_ip = re.search(r'inet (192\.168\.2\.\d+)',
                   subprocess.run(['ifconfig'], capture_output=True, text=True).stdout).group(1)
srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('0.0.0.0', port))
srv.listen(1)
srv.settimeout(60)
stats = {}


def serve():
    conn, _ = srv.accept()
    t0 = time.time()
    with open(path, 'rb') as fh:
        sent = conn.sendfile(fh)
    conn.shutdown(socket.SHUT_WR)
    conn.close()
    stats['sent'], stats['secs'] = sent, time.time() - t0


th = threading.Thread(target=serve)
th.start()
out = subprocess.run(['python3', '-I', '/tmp/rmx3370-scout/tn.py',
                      f'nc {mac_ip} {port} | {pipeline}', str(timeout)],
                     capture_output=True, text=True).stdout
th.join(timeout=5)
srv.close()
if 'sent' in stats:
    print(f"sent {stats['sent']} of {os.path.getsize(path)} bytes in {stats['secs']:.1f}s "
          f"({stats['sent'] / stats['secs'] / 2**20:.1f} MiB/s)")
print(out[-1500:])
