#!/usr/bin/bash
set -eu
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
work=/workspace/tinyagent-c-probe-20260908
mkdir "$work"
cd "$work"
printf 'provider=%s\ncwd=%s\n' "$TINYAGENT_EXECUTION_PROVIDER" "$PWD"
awk '/^(Pid|PPid|Uid):/ {print}' /proc/self/status
cat > main.c <<'C'
#include <stdio.h>
int main(void) { printf("%d\n", 6 * 6); return 0; }
C
cat > Makefile <<'MAKE'
sample: main.c
	cc -Wall -Wextra -Werror main.c -o sample
test: sample
	test "$$(./sample)" = 42
MAKE
cp main.c before.c
set +e
make test
before=$?
set -e
printf 'before_exit=%s\n' "$before"
test "$before" -ne 0
sed -i 's/6 \* 6/6 * 7/' main.c
make test
printf 'after_exit=0\n'
set +e
git diff --no-index before.c main.c
changed=$?
set -e
test "$changed" = 1
sha256sum before.c main.c sample
printf 'development_loop_exit=0\n'
