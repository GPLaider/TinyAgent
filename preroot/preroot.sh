#!/system/bin/sh
# TinyAgent PreRoot 0.1.0: Android-owned Fedora execution entrypoint.
set -eu
fail() { printf 'PreRoot: %s\n' "$*" >&2; exit 1; }
test "$(id -u)" = 0 || fail 'root ADB is required'
test "$#" -ge 3 || fail 'usage: preroot.sh ROOT unrestricted-root doctor|exec [CWD COMMAND ARGS...]'
root=$1
mode=$2
action=$3
shift 3
case "$root" in /data/local/*) ;; *) fail 'root must be below /data/local';; esac
test "$(realpath "$root")" = "$root" || fail 'root must be canonical'
test "$mode" = unrestricted-root || fail 'this runtime implements unrestricted-root only; no silent escalation'
test -f "$root/etc/fedora-release" || fail 'Fedora is not prepared'
test -x "$root/usr/bin/env" || fail 'Fedora env is missing'
case "$action" in
  doctor)
    test "$#" -eq 0 || fail 'doctor takes no command'
    printf 'preroot=0.1.0\nprovider=fedora-preroot\nandroid_provider=android-self-adb\n'
    printf 'serial=%s\nandroid=%s\nuid=%s\nmode=%s\nroot=%s\n' \
      "$(getprop ro.serialno)" "$(getprop ro.build.version.release)" "$(id -u)" "$mode" "$root"
    cat "$root/etc/fedora-release"
    exit 0
    ;;
  exec)
    test "$#" -ge 2 || fail 'exec requires CWD and COMMAND'
    case "$1" in /*) ;; *) fail 'CWD must be absolute inside Fedora';; esac
    ;;
  serve)
    test "$#" -eq 0 || fail 'serve takes no extra arguments'
    set -- /workspace /usr/local/bin/opencode serve --hostname 127.0.0.1 --port 4096
    ;;
  *) fail 'unknown action';;
esac
# Always create the namespace here; callers cannot bypass it with an env flag.
exec unshare -m /system/bin/sh "$(dirname "$(realpath "$0")")/enter.sh" "$root" "$@"
