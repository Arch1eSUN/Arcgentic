#!/usr/bin/env bash
# scripts/lib/python.sh — choose a usable Python interpreter for Arcgentic scripts.

set -uo pipefail

arcgentic_python() {
  local candidates=()
  if [ -n "${ARCGENTIC_PYTHON:-}" ]; then
    candidates+=("$ARCGENTIC_PYTHON")
  fi
  candidates+=("/opt/anaconda3/bin/python3")
  candidates+=("/usr/bin/python3")

  local path_python
  path_python="$(command -v python3 2>/dev/null || true)"
  if [ -n "$path_python" ]; then
    candidates+=("$path_python")
  fi

  local py seen=" " required_modules=("$@")
  for py in "${candidates[@]}"; do
    [ -n "$py" ] || continue
    case "$seen" in
      *" $py "*) continue ;;
    esac
    seen="$seen$py "
    [ -x "$py" ] || continue
    if "$py" -c 'import importlib, sys; [importlib.import_module(m) for m in sys.argv[1:]]' "${required_modules[@]}" >/dev/null 2>&1; then
      printf '%s\n' "$py"
      return 0
    fi
  done

  echo "Error: no usable Python interpreter found for modules: ${required_modules[*]:-(none)}" >&2
  return 1
}
