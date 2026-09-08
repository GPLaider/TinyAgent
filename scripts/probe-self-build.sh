#!/usr/bin/bash
# Read-only inventory inside the app-managed Fedora environment.
set -eu
printf 'provider=%s\npermission=%s\ncwd=%s\npid=%s\n' \
  "$TINYAGENT_EXECUTION_PROVIDER" "$TINYAGENT_PERMISSION" "$PWD" "$$"
uname -m
cat /etc/fedora-release
df -Pk /workspace /tmp
for tool in java javac git python3 make gcc microdnf aapt2; do
  if command -v "$tool"; then :; else printf 'missing=%s\n' "$tool"; fi
done
printf 'DNS configuration\n'
cat /etc/resolv.conf
printf 'HTTPS probe\n'
curl -fsSL --max-time 20 -o /dev/null -w 'fedora_https=%{http_code}\n' https://fedoraproject.org/
