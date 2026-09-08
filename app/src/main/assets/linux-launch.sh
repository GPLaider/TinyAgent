#!/system/bin/sh
set -eu
printf '%s\n' "$$" > "$1"
shift
exec "$@"
