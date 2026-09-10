#!/system/bin/sh
set -eu
record=$1
shift
{
  printf '%s\n' "$$"
  cat /proc/sys/kernel/random/boot_id
  cat "/proc/$$/stat"
} > "$record.tmp"
mv "$record.tmp" "$record"
exec "$@"
