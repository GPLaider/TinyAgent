#!/system/bin/sh
# App bridge invokes this only after fresh self-device and execution-UID proof.
set -eu
action=$1
directory=$2
case "$directory" in /data/local/tmp/tinyagent-android-*/????????-????-????-????-????????????) ;; *) exit 64;; esac
case "$directory" in *[!a-z0-9/_-]*) exit 64;; esac
parent=${directory%/*}
umask 077

identity() {
    test -f "$directory/pid" || return 1
    read -r pid born < "$directory/pid"
    case "$pid:$born" in *[!0-9:]*|:*) return 1;; esac
    test "$pid" -gt 1 || return 1
    test -r "/proc/$pid/stat" || return 1
    stat=$(cat "/proc/$pid/stat") || return 1
    set -- ${stat##*) }
    test "$3" = "$pid" && test "$4" = "$pid" || return 1
    shift 19
    test "$1" = "$born"
}

group_alive() {
    read -r pid born < "$directory/pid" || return 2
    case "$pid:$born" in *[!0-9:]*|:*) return 2;; esac
    groups=$(/system/bin/toybox ps -A -o PGID) || return 2
    printf '%s\n' "$groups" | awk -v target="$pid" 'NR>1 && $1==target {found=1} END {exit !found}'
}

case "$action" in
start)
    test "$#" = 4 || exit 64
    test ! -L "$parent" || exit 65
    mkdir -p "$parent"
    test "$(stat -c %u "$parent")" = "$(id -u)" || exit 65
    chmod 700 "$parent"
    # Exclusive UUID directory: an uncertain start is inspected, never repeated.
    mkdir "$directory"
    printf '%s' "$3" | base64 -d > "$directory/command"
    printf '%s' "$4" | base64 -d > "$directory/cwd"
    cat > "$directory/worker" <<'WORKER'
#!/system/bin/sh
set -u
directory=$1
umask 077
stat=$(cat /proc/$$/stat)
set -- ${stat##*) }
shift 19
printf '%s %s\n' "$$" "$1" > "$directory/pid.tmp"
mv "$directory/pid.tmp" "$directory/pid"
if test -e "$directory/cancel"; then exit 125; fi
cd "$(cat "$directory/cwd")" || { echo 126 > "$directory/exit"; exit 126; }
/system/bin/sh "$directory/command"
code=$?
printf '%s\n' "$code" > "$directory/exit.tmp"
mv "$directory/exit.tmp" "$directory/exit"
exit "$code"
WORKER
    # Only the generated worker is launched; no interactive shell is exposed.
    trap '' HUP
    /system/bin/toybox setsid /system/bin/sh "$directory/worker" "$directory" </dev/null >"$directory/stdout" 2>"$directory/stderr" &
    echo started
    ;;
cancel)
    test -d "$directory" && test ! -L "$directory" || exit 66
    : > "$directory/cancel"
    # Wait for a just-starting worker to publish its identity; don't kill by name.
    attempts=0
    while test ! -f "$directory/pid" && test "$attempts" -lt 3; do sleep 1; attempts=$((attempts+1)); done
    if identity; then
        /system/bin/toybox kill -TERM -- "-$pid" || true
        sleep 1
        if identity; then /system/bin/toybox kill -KILL -- "-$pid" || true; fi
    fi
    ;;
status)
    test -d "$directory" && test ! -L "$directory" || exit 66
    state=unknown
    code=-1
    if test -f "$directory/exit"; then
        read -r code < "$directory/exit"
        case "$code" in ''|*[!0-9]*) exit 65;; esac
        state=completed
    elif identity; then
        state=running
    elif test -f "$directory/pid" && test -f "$directory/cancel"; then
        if group_alive; then state=unknown; else
            result=$?
            test "$result" != 1 || state=cancelled
        fi
    elif test ! -f "$directory/pid"; then
        state=starting
    fi
    # The worker can publish exit and disappear between the first two checks.
    if test "$state" = unknown && test -f "$directory/exit"; then
        read -r code < "$directory/exit"
        case "$code" in ''|*[!0-9]*) exit 65;; esac
        state=completed
    fi
    if test "$state" = completed && test -f "$directory/pid"; then
        if group_alive; then state=running; else
            result=$?
            test "$result" = 1 || state=unknown
        fi
    fi
    printf '%s\n%s\n' "$state" "$code"
    tail -c 32768 "$directory/stdout" | base64 | tr -d '\n'
    printf '\n'
    tail -c 32768 "$directory/stderr" | base64 | tr -d '\n'
    printf '\n'
    ;;
*) exit 64;;
esac
