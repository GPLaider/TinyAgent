from pathlib import Path
import subprocess
import json

task = Path('/home/admin/dnfast-memfd-664e-20260911')
output = Path('/home/admin/tinyagent-dnfast-target-tree-20260911')
output.mkdir(exist_ok=True)
image = 'c28b19557813d8661856cbd612e53dc7600a2009dad2094555ff3adf70fdf6f9'
argv = ['podman', 'run', '--rm', '--pull=never', '--read-only', '--network=none',
        '--security-opt=label=disable', '--userns=keep-id', '--user=1000',
        '-v', str(task)+':/work:ro', '--workdir=/work/source',
        '--env=CARGO_HOME=/work/cargo-home', '--env=HOME=/tmp', image,
        'cargo', 'tree', '--locked', '--offline', '--target=aarch64-unknown-linux-gnu',
        '-p', 'dnfast-cli', '-p', 'dnfast-executor', '--edges=normal,build', '--prefix=none', '--format={p}']
result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
(output/'tree.txt').write_text(result.stdout)
(output/'stderr.txt').write_text(result.stderr)
(output/'invocation.json').write_text(json.dumps({'argv':argv,'exit':result.returncode}, indent=2))
print(json.dumps({'exit':result.returncode,'lines':len(result.stdout.splitlines()),'error':result.stderr[-1500:]}))
raise SystemExit(result.returncode)
