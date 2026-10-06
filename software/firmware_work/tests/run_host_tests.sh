#!/bin/sh
set -eu
exec /bin/bash "$(dirname "$0")/../../scripts/test_host.sh"
