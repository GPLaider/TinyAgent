"""Run inside app-owned Fedora: obtain Android facts, process and persist the result."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

assert os.environ['TINYAGENT_EXECUTION_PROVIDER'] == 'fedora-local'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=['stock', 'developer', 'root'], default='root')
parser.add_argument('--run', default='integration-20260908')
args = parser.parse_args()
assert re.fullmatch(r'[a-zA-Z0-9-]+', args.run), 'Invalid evidence directory'
tool = Path('/root/.tinyagent/ANDROID_TOOL.md').read_text()
socket = re.search(r'tinyagent-android-\d+-\d+', tool).group()
command = ['curl', '--fail-with-body', '--silent', '--show-error', '--max-time', '90',
           '--abstract-unix-socket', socket, 'http://localhost/inspect/'+args.mode]
response = subprocess.run(command, capture_output=True, text=True, timeout=95, check=True)
android = json.loads(response.stdout)
assert android['environment'] == 'android' and android['mode'] == args.mode
actual_uid = int(re.search(r'^Uid:\s+(\d+)', Path('/proc/self/status').read_text(), re.M).group(1))
assert actual_uid == android['app_uid'] and actual_uid != 0
if args.mode == 'stock':
    assert android['execution_uid'] == actual_uid and android['authority'] == 'app-sandbox'
else:
    assert android['verified_self'] and android['execution_uid'] == (0 if args.mode == 'root' else 2000)
directory = Path('/shared') / args.run
directory.mkdir(exist_ok=True)
raw = directory / 'android-inspection.json'
raw.write_text(response.stdout)
result = dict(mode=args.mode, source_environment='android', processed_environment='fedora-local', device=android['device'],
              model=android['model'], sdk=android['sdk'], android_execution_uid=android['execution_uid'],
              fedora_actual_android_uid=actual_uid, source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
processed = directory / 'processed-android.json'
processed.write_text(json.dumps(result, indent=2)+'\n')
assert json.loads(processed.read_text()) == result
print(json.dumps(dict(command=command, command_exit=response.returncode, result=result,
                     output_path=str(processed), output_sha256=hashlib.sha256(processed.read_bytes()).hexdigest()), indent=2))
