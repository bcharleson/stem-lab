#!/usr/bin/env bash
# Fail if the public tree contains audio, secrets, or machine home paths.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail=0

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  tracked="$(git ls-files)"
else
  tracked="$(git ls-files --error-unmatch . 2>/dev/null || find . -type f \
    -not -path './.git/*' -not -path './.venv/*' -not -path './work/*' \
    -not -path './output/*' -not -path '*/__pycache__/*')"
fi

audio="$(printf '%s\n' "$tracked" | grep -Ei '\.(m4a|mp3|wav|flac|aiff|aif|ogg|aac|wma|caf|alac)$' || true)"
if [[ -n "$audio" ]]; then
  echo "Audio files must not be committed:" >&2
  printf '%s\n' "$audio" >&2
  fail=1
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git grep -nE '/Users/|/home/[A-Za-z0-9._-]+/' -- . ':!scripts/check-oss.sh' >/dev/null 2>&1; then
    echo "Tracked files contain absolute home paths:" >&2
    git grep -nE '/Users/|/home/[A-Za-z0-9._-]+/' -- . ':!scripts/check-oss.sh' >&2 || true
    fail=1
  fi
  if git grep -nEi 'api[_-]?key|secret[_-]?key|BEGIN (RSA |OPENSSH )?PRIVATE' -- . >/dev/null 2>&1; then
    echo "Tracked files look like they contain secrets:" >&2
    git grep -nEi 'api[_-]?key|secret[_-]?key|BEGIN (RSA |OPENSSH )?PRIVATE' -- . >&2 || true
    fail=1
  fi
fi

if [[ "$fail" -ne 0 ]]; then
  exit 1
fi
echo "OSS tree looks clean."
