"""Correlate the retained phone tool timestamps with the observed screen-off interval."""
import json
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[1]
path = root/'evidence/lyriq1-luna-screenoff.json'
record = json.loads(path.read_text())
adb = str(Path.home()/'AppData/Local/Android/Sdk/platform-tools/adb.exe')
assert subprocess.check_output([adb, '-s', record['serial'], 'shell', 'getprop', 'ro.serialno'], text=True).strip() == record['device']
started = time.time_ns() // 1_000_000
device_ms = int(subprocess.check_output([adb, '-s', record['serial'], 'shell', 'date', '+%s%3N'], text=True).strip())
ended = time.time_ns() // 1_000_000
offset = device_ms - (started + ended) // 2
assert abs(offset) < 5000, 'Clock difference requires separate investigation'
probe = json.loads((root/'evidence'/f"{record['session']}-probe.json").read_text())
assert probe['status']['type'] == 'idle'
tools = [p for message in probe['messages'] for p in message['parts'] if p['type'] == 'tool']
inside = [dict(tool=p['tool'], time=p['state']['time'], exit=p['state'].get('metadata', {}).get('exit'))
          for p in tools if p['state']['status'] == 'completed'
          and record['offObservedHostMs'] + offset + 5000 < p['state']['time']['start']
          and p['state']['time']['end'] < record['wakeRequestedHostMs'] + offset - 5000]
assert any(p['tool'] == 'bash' and p['exit'] == 0 for p in inside), 'No successful shell work well within screen-off interval'
record.update(status='Model repair passed; completed tools observed within the recorded screen-off interval',
              completedToolsInsideInterval=inside, clockOffsetMsAtReadback=offset,
              clockMeasurementRoundTripMs=ended-started,
              scope='One 144-second screen-off interval. Clock offset measured at readback; assumes no intervening clock step. Not long Doze or network-transition acceptance.')
path.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(dict(completed_tools_inside=len(inside), clock_offset_ms=offset, passed=True)))
