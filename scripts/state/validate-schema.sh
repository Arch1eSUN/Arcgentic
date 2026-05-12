#!/usr/bin/env bash
# scripts/state/validate-schema.sh — validate state.yaml against
# schema/state.schema.json using Python jsonschema.
#
# Usage: validate-schema.sh STATE_FILE [--schema PATH]
# Default schema: $ARCGENTIC_ROOT/schema/state.schema.json
# Exit 0 if valid, 1 if invalid (with error printed to stderr).

set -uo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 STATE_FILE [--schema PATH]" >&2
  exit 2
fi

STATE_FILE="$1"; shift
SCHEMA_FILE="${ARCGENTIC_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}/schema/state.schema.json"

while [ $# -gt 0 ]; do
  case "$1" in
    --schema) SCHEMA_FILE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ ! -f "$STATE_FILE" ]; then
  echo "Error: state file not found: $STATE_FILE" >&2
  exit 1
fi
if [ ! -f "$SCHEMA_FILE" ]; then
  echo "Error: schema file not found: $SCHEMA_FILE" >&2
  exit 1
fi

python3 - "$STATE_FILE" "$SCHEMA_FILE" <<'PY'
import sys, json, yaml
from jsonschema import Draft202012Validator
state_file, schema_file = sys.argv[1], sys.argv[2]
with open(state_file) as f:
    data = yaml.safe_load(f) or {}
with open(schema_file) as f:
    schema = json.load(f)
v = Draft202012Validator(schema)
errors = sorted(v.iter_errors(data), key=lambda e: e.path)
if errors:
    for e in errors:
        path = "/".join(str(p) for p in e.path) or "(root)"
        print(f"  • {path}: {e.message}", file=sys.stderr)
    sys.exit(1)
print(f"valid: {state_file}")
sys.exit(0)
PY
