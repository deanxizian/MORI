#!/bin/sh
# Read-only. Run manually on an explicitly authorized Tencent host. No SSH/login,
# firewall edits, package installs, service changes or secret values are performed.
set -eu
uname -a
getconf _NPROCESSORS_ONLN
if test -r /proc/meminfo; then head -5 /proc/meminfo; fi
df -h .
command -v docker >/dev/null 2>&1 && docker --version || true
command -v docker >/dev/null 2>&1 && docker compose version || true
command -v ss >/dev/null 2>&1 && ss -lnt || true
