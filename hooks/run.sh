#!/bin/sh
# Resolve an interpreter, run one hook mode, and never fail the tool call.
root="${CLAUDE_PLUGIN_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

if [ "${UNWORDY_OFF:-}" = "1" ]; then
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  py=python3
elif command -v python >/dev/null 2>&1; then
  py=python
elif command -v uv >/dev/null 2>&1; then
  py="uv run --no-project python"
else
  exit 0
fi

PYTHONPATH="$root${PYTHONPATH:+:$PYTHONPATH}" $py -m unwordy.hook "$@"
exit 0
