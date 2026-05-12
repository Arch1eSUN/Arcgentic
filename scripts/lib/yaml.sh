#!/usr/bin/env bash
# scripts/lib/yaml.sh — YAML read/write helpers via embedded Python3 + PyYAML.
#
# Why Python: yq is not universally installed; Python3 + PyYAML is.
# All functions are deterministic + side-effect-only-via-stdout/file-arg.
#
# Public API:
#   yaml_get FILE.yaml dot.path.expr             → stdout the value (or empty if missing)
#   yaml_set FILE.yaml dot.path.expr VALUE       → in-place mutation
#   yaml_append_to_list FILE.yaml dot.path.expr JSON_OBJ → append object to a list
#   yaml_to_json FILE.yaml                       → stdout the JSON equivalent
#
# All functions exit nonzero on parse error.

set -uo pipefail

yaml_get() {
  local file="$1" path="$2"
  python3 - "$file" "$path" <<'PY'
import sys, yaml
file, path = sys.argv[1], sys.argv[2]
with open(file) as f:
    data = yaml.safe_load(f) or {}
parts = [p for p in path.split('.') if p]
cur = data
for p in parts:
    if isinstance(cur, dict) and p in cur:
        cur = cur[p]
    elif isinstance(cur, list):
        try:
            cur = cur[int(p)]
        except (ValueError, IndexError):
            sys.exit(0)  # missing → empty stdout
    else:
        sys.exit(0)
if cur is None:
    sys.exit(0)
if isinstance(cur, (dict, list)):
    import json
    print(json.dumps(cur))
else:
    print(cur)
PY
}

yaml_set() {
  local file="$1" path="$2" value="$3"
  python3 - "$file" "$path" "$value" <<'PY'
import sys, yaml, json
file, path, raw = sys.argv[1], sys.argv[2], sys.argv[3]
with open(file) as f:
    data = yaml.safe_load(f) or {}
parts = [p for p in path.split('.') if p]
# Try JSON-decode the value; fall back to raw string
try:
    value = json.loads(raw)
except json.JSONDecodeError:
    value = raw
cur = data
for p in parts[:-1]:
    if p not in cur or not isinstance(cur[p], dict):
        cur[p] = {}
    cur = cur[p]
cur[parts[-1]] = value
with open(file, 'w') as f:
    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
PY
}

yaml_append_to_list() {
  local file="$1" path="$2" json_obj="$3"
  python3 - "$file" "$path" "$json_obj" <<'PY'
import sys, yaml, json
file, path, raw = sys.argv[1], sys.argv[2], sys.argv[3]
with open(file) as f:
    data = yaml.safe_load(f) or {}
parts = [p for p in path.split('.') if p]
cur = data
for p in parts[:-1]:
    cur = cur.setdefault(p, {})
key = parts[-1]
if key not in cur or not isinstance(cur[key], list):
    cur[key] = []
cur[key].append(json.loads(raw))
with open(file, 'w') as f:
    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
PY
}

yaml_to_json() {
  local file="$1"
  python3 - "$file" <<'PY'
import sys, yaml, json
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f) or {}
print(json.dumps(data, indent=2))
PY
}
