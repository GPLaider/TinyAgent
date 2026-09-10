"""Re-run the failed Configure step using its supported canonical interpreter override."""
import os
from pathlib import Path
import subprocess
assert os.environ.get('TINYAGENT_EXECUTION_PROVIDER') == 'fedora-local'
base = Path('/workspace/tinyagent-six-builds/appflowy/frontend/rust-lib/target/aarch64-linux-android/debug/build')
paths = list(base.glob('openssl-sys-*/out/openssl-build/build/src/Configure'))
assert len(paths) == 1
result = subprocess.run(['/usr/bin/perl', './Configure', 'linux-aarch64'], cwd=paths[0].parent,
                        env=dict(os.environ, PERL='/usr/bin/perl'), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(result.stdout)
assert result.returncode == 0
print('PERL=/usr/bin/perl: OpenSSL Configure passed; full Android build remains separate')
