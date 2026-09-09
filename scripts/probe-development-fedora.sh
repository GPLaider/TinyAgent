#!/usr/bin/bash
set -eu
test "$(id -u)" = 0
test -f /workspace/android-device.txt
project=/workspace/smoke-20260908
test ! -e "$project"
mkdir "$project"
cd "$project"
git init -q
cat > main.c <<'SOURCE'
#include <stdio.h>
int main(void) { printf("%d\n", 41 - 1); return 0; }
SOURCE
cat > Makefile <<'BUILD'
app: main.c
	$(CC) -Wall -Wextra -Werror main.c -o app
test: app
	python3 -c 'import subprocess; actual=subprocess.check_output(["./app"]).decode().strip(); assert actual == "42", actual'
BUILD
git add main.c Makefile
if make test > before.log 2>&1; then
  echo 'Expected the initial assertion to fail' >&2
  exit 1
fi
grep -q 'AssertionError: 40' before.log
printf 'BEFORE: expected assertion failure verified\n'
cat before.log
python3 - <<'EDIT'
from pathlib import Path
source = Path('main.c')
text = source.read_text()
assert text.count('41 - 1') == 1
source.write_text(text.replace('41 - 1', '41 + 1'))
EDIT
git diff -- main.c > change.patch
test -s change.patch
make test > after.log 2>&1
printf 'AFTER: actual rebuild and assertion passed\n'
cat after.log
cat change.patch
python3 - <<'PROCESS'
import json, os, subprocess
from pathlib import Path
android = dict(line.split('=', 1) for line in Path('/workspace/android-device.txt').read_text().splitlines())
assert android['serial'] == 'ZY22HZPLL8' and android['device'] == 'lyriq'
result = dict(android=android, fedora_arch=os.uname().machine, cwd=str(Path.cwd()),
              compiled_result=int(subprocess.check_output(['./app'])), test='passed')
assert result['fedora_arch'] == 'aarch64' and result['compiled_result'] == 42
Path('android-summary.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
PROCESS
git --version
python3 --version
gcc --version | head -n 1
