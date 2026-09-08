#!/system/bin/sh
set -eu
umask 077
base64 -d "$1" > "$2"
chmod 600 "$2"
