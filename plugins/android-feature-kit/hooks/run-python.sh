#!/usr/bin/env bash
# Runs a hook script with the first Python 3.8+ on PATH (python3, python or py), passing stdin
# through. Without Python the hook exits 0 and the call goes ahead: the layer guard is a
# guardrail, and the repository's pre-commit and CI checks are the boundary.
script="$1"
shift
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' </dev/null >/dev/null 2>&1; then
    exec "$candidate" "$script" "$@"
  fi
done
echo "android-feature-kit: no Python 3.8+ found; the layer guard did not run." >&2
exit 0
