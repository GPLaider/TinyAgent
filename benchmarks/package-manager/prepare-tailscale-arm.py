"""Port the pinned gomobile host selector to the supplied Linux ARM64 NDK."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
source = Path('/workspace/tinyagent-six-builds/tailscale-android')
assert Path.cwd() == source and os.uname().machine == 'aarch64'
go = ['/usr/bin/bash', './tool/go']
cache = Path(subprocess.check_output(go+['env', 'GOMODCACHE'], text=True).strip())
version = 'v0.0.0-20240806205939-81131f6468ab'
original = cache/('golang.org/x/mobile@'+version)
target = Path('/workspace/tinyagent-toolchain-patches/gomobile-'+version)
if not target.exists():
    shutil.copytree(original, target)
    for path in target.rglob('*'):
        if path.is_file(): path.chmod(0o644)
old = (original/'cmd/gomobile/env.go').read_text()
needle = '\t\tcase "arm64":\n'
start = old.index('func archNDK() string')
end = old.index('\ntype ndkToolchain', start)
host_selector = old[start:end]
assert host_selector.count(needle) == 1
new = old[:start]+host_selector.replace(needle, needle+'\t\t\tif runtime.GOOS == "linux" {\n\t\t\t\tarch = "arm64"\n\t\t\t\tbreak\n\t\t\t}\n')+old[end:]
(target/'cmd/gomobile/env.go').write_text(new)
(target/'tinyagent-arm.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/cmd/gomobile/env.go', tofile='b/cmd/gomobile/env.go')))
(target/'tinyagent-source.json').write_text(json.dumps(dict(module_version=version, original_env_sha256=hashlib.sha256(old.encode()).hexdigest(), modified_env_sha256=hashlib.sha256(new.encode()).hexdigest())))
subprocess.run(go+['mod', 'edit', '-replace=golang.org/x/mobile='+str(target)], check=True)
(target/'cmd/gomobile/tinyagent_arm_test.go').unlink(missing_ok=True)
(target/'cmd/gomobile/tinyagent_host_test.go').write_text('package main\nimport "testing"\nfunc TestTinyAgentArmNDK(t *testing.T) { if archNDK() != "linux-arm64" { t.Fatal(archNDK()) } }\n')
result = subprocess.run(go+['test', '-json', 'golang.org/x/mobile/cmd/gomobile', '-run', '^TestTinyAgentArmNDK$', '-count=1'], check=True, capture_output=True, text=True)
events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
assert any(e.get('Test') == 'TestTinyAgentArmNDK' and e.get('Action') == 'pass' for e in events), 'Required regression test did not run'
print('TestTinyAgentArmNDK executed and passed')
print('Pinned gomobile Linux ARM64 host patch applied; module cache unchanged')
