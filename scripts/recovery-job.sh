#!/usr/bin/bash
set -eu
printf '%s\n' "$$" > /shared/recovery-job.pid
exec /usr/bin/sleep 120
