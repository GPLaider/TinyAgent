"""Observe actual dnfast TCP counters; proc io is not socket receive progress."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time

adb = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
serial = '100.79.65.42:5555'
native = sys.argv[1:] == ['--native']
assert not sys.argv[1:] or native
def call(*args):
    return subprocess.check_output([str(adb), '-s', serial, *args], timeout=30).decode()

assert call('shell', 'getprop', 'ro.serialno').strip() == 'ZY22HZPLL8'
samples = []
started = time.monotonic()
for index in range(7):
    processes = call('shell', 'ps', '-A', '-o', 'UID,PID,NAME').splitlines()
    name = 'io.github.gplaider.tinyagent.debug' if native else 'dnfast'
    pids = [line.split()[1] for line in processes if re.fullmatch(r'10151\s+\d+\s+' + re.escape(name), line.strip())]
    sockets = call('shell', 'ss', '-tinp').splitlines()
    received = []
    for i, line in enumerate(sockets[:-1]):
        for pid in pids:
            match = re.search(r'pid=' + pid + r',fd=(\d+)\)', line)
            count = re.search(r'bytes_received:(\d+)', sockets[i + 1])
            if match and count:
                received.append({'pid': int(pid), 'fd': int(match[1]), 'bytes_received': int(count[1])})
    power = call('shell', 'dumpsys', 'power')
    wake = re.search(r'^  mWakefulness=(\w+)', power, re.MULTILINE)
    sample = {'elapsed_seconds': round(time.monotonic() - started, 2),
              'wakefulness': wake[1] if wake else None, 'sockets': received}
    samples.append(sample)
    path = 'evidence/bb7ca11-screen-off-' + ('native-' if native else '') + 'tcp.json'
    Path(path).write_text(json.dumps(samples, indent=2))
    print(json.dumps(sample), flush=True)
    if not pids or index == 6:
        break
    time.sleep(10)
