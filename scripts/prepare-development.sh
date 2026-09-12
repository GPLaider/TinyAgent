#!/usr/bin/bash
set -eu
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
scripts=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
trap 'status=$?; printf "development_prepare_exit=%s\n" "$status"' EXIT
printf '1/3 Fedora development packages and Java\n'
/usr/bin/bash "$scripts/prepare-self-build.sh"
python3 "$scripts/tinyagent-packages.py" install nodejs gnupg2
printf '2/3 Download and verify Android SDK\n'
python3 "$scripts/prepare-android-sdk-fedora.py"
printf '3/3 Configure ARM64 Android build tools\n'
python3 "$scripts/configure-android-sdk-fedora.py"
