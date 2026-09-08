#!/usr/bin/env bash
# Host-only guard test. These identity functions do not represent a phone.
set -eu
id() { printf '%s\n' "$TEST_UID"; }
getprop() { printf '%s\n' "$TEST_ABI"; }
export -f id getprop
exec bash "$@"
