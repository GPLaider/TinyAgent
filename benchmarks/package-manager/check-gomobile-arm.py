"""Run the previously skipped ARM64 regression without changing production Go sources."""
import json
import os
from pathlib import Path
import subprocess

assert os.uname().machine == 'aarch64'
assert os.environ['TINYAGENT_EXECUTION_PROVIDER'] == 'fedora-local'
root = Path('/workspace/tinyagent-toolchain-patches/gomobile-v0.0.0-20240806205939-81131f6468ab/cmd/gomobile')
old = root/'tinyagent_arm_test.go'
target = root/'tinyagent_host_test.go'
if old.exists():
    assert 'func TestTinyAgentArmNDK' in old.read_text()
    assert not target.exists() or target.read_bytes() == old.read_bytes()
    old.rename(target)
result = subprocess.run(['/usr/bin/bash', './tool/go', 'test', '-json',
                         'golang.org/x/mobile/cmd/gomobile', '-run', '^TestTinyAgentArmNDK$', '-count=1'],
                        cwd='/workspace/tinyagent-six-builds/tailscale-android',
                        capture_output=True, text=True, check=True)
events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
assert any(e.get('Test') == 'TestTinyAgentArmNDK' and e.get('Action') == 'pass' for e in events)
print(result.stdout)
