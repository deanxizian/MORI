#!/bin/sh
# Prefer the user's runtime; bundled desktop runtime is a local fallback.
if ! command -v node >/dev/null 2>&1; then
  PATH="/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH"
  export PATH
fi
if command -v pnpm >/dev/null 2>&1; then exec pnpm "$@"; fi
exec /Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm "$@"
