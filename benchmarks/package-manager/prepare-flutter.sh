#!/usr/bin/bash
set -eu
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
test "$(uname -m)" = aarch64
base=/opt/tinyagent-build
# Share the native preparation lock: Flutter's bootstrap calls `which`.
printf 'Waiting for native host prerequisites\n'
exec 8>/workspace/tinyagent-six-builds/.native-preparation.lock
flock 8
command -v which
flock -u 8
flutter="$base/flutter-3.27.4"
revision=d8a9f9a52e5af486f80d932e838ee93861ffd863
exec 9>"$base/.flutter-prepare.lock"
flock -n 9
trap 'status=$?; printf "flutter_preparation_exit=%s\n" "$status"' EXIT
if test ! -d "$flutter"; then
  git clone --depth 1 --branch 3.27.4 https://github.com/flutter/flutter.git "$flutter"
fi
test "$(git -C "$flutter" rev-parse HEAD)" = "$revision"
export FLUTTER_SUPPRESS_ANALYTICS=true
export CI=true
"$flutter/bin/flutter" --version
"$flutter/bin/flutter" precache --android
printf 'flutter_source=%s\n' "$revision"
