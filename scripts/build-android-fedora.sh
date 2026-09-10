#!/usr/bin/bash
# Android build runs entirely inside the phone's Fedora workspace.
set -eu
case "${TINYAGENT_EXECUTION_PROVIDER:-}" in fedora-preroot|fedora-local) ;; *) exit 1;; esac
test "$(uname -m)" = aarch64
cd "$(dirname "$(realpath "$0")")/.."
export JAVA_HOME=${JAVA_HOME:-/opt/tinyagent-build/jdk-17.0.20.1+1}
export PATH="$JAVA_HOME/bin:$PATH"
variant=${TINYAGENT_BUILD_TYPE:-debug}
case "$variant" in
  debug) task=:app:assembleDebug ;;
  release)
    task=:app:assembleRelease
    test -n "${TINYAGENT_RELEASE_SIGNING_PROPERTIES:-}" && test -r "$TINYAGENT_RELEASE_SIGNING_PROPERTIES" || {
      printf 'Release signing properties are required; never generate a replacement identity on the phone.\n' >&2
      exit 1
    }
    ;;
  *) printf 'TINYAGENT_BUILD_TYPE must be debug or release.\n' >&2; exit 1 ;;
esac
if test "$TINYAGENT_EXECUTION_PROVIDER" = fedora-local; then
  if test "$variant" = debug; then
    export TINYAGENT_SIGNING_PROPERTIES=${TINYAGENT_SIGNING_PROPERTIES:-/root/.tinyagent/signing/development.properties}
    if test ! -r "$TINYAGENT_SIGNING_PROPERTIES"; then
    printf 'Shared development signing identity is missing. Provision it before building an update.\n' >&2
    exit 1
    fi
  fi
  export ANDROID_HOME=/opt/tinyagent-build/android-sdk
  aapt2=/opt/tinyagent-build/sdk-inputs/arm64.tar.xz.unpacked/android-sdk/build-tools/37.0.0/aapt2
  test -x "$aapt2"
  set -- "-Pandroid.aapt2FromMavenOverride=$aapt2" "$@"
fi
printf 'provider=%s\ncwd=%s\npid=%s\n' "$TINYAGENT_EXECUTION_PROVIDER" "$PWD" "$$"
git rev-parse HEAD
git status --short
exec /usr/bin/bash ./gradlew --no-daemon --max-workers=2 \
  '-Dorg.gradle.jvmargs=-Xmx1536m' :app:clean "$task" "$@"
