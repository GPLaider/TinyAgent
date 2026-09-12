#!/usr/bin/bash
# Run inside PreRoot. DNS addresses must come from Android's current network.
set -eu
case "${TINYAGENT_EXECUTION_PROVIDER:-}" in fedora-preroot|fedora-local) ;; *) exit 1;; esac
test "$(uname -m)" = aarch64
test "$(id -u)" = 0
test ! -L /etc/resolv.conf
for address in "$@"; do
  case "$address" in ''|*[!0-9a-fA-F.:]*) echo 'Invalid DNS address' >&2; exit 1;; esac
done
umask 022
if test "$#" -gt 0; then
dns=$(mktemp /etc/resolv.conf.XXXXXX)
trap 'rm -f "$dns"' EXIT
for address in "$@"; do printf 'nameserver %s\n' "$address"; done > "$dns"
printf 'options timeout:2 attempts:2\n' >> "$dns"
mv "$dns" /etc/resolv.conf
fi
curl -fsSL --max-time 25 -o /dev/null -w 'fedora_https=%{http_code}\n' https://fedoraproject.org/
scripts=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$scripts/tinyagent-packages.py" install git python3 make gcc unzip tar gzip
# Fedora 44 ships Java 25+, while this source uses Gradle 8.13. Keep JDK 17.
# Official Adoptium API metadata recorded 2026-09-08; archive is verified first.
jdk=/opt/tinyagent-build/jdk-17.0.20.1+1
mkdir -p /opt/tinyagent-build
if test ! -x "$jdk/bin/javac"; then
  archive=/opt/tinyagent-build/temurin17.tar.gz
  curl -fL --retry 2 --connect-timeout 20 --max-time 900 \
    -o "$archive" 'https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_aarch64_linux_hotspot_17.0.20.1_1.tar.gz'
  printf '457b57af8f9c93ec39080bb8c764f559dc8c89a6da1a39d718a400b7890d3e41  %s\n' "$archive" | sha256sum -c -
  tar -xzf "$archive" -C /opt/tinyagent-build
fi
"$jdk/bin/java" -version
"$jdk/bin/javac" -version
git --version
python3 --version
printf 'Base development tools prepared; run SDK preparation next.\n'
