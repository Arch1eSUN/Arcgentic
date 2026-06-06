#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TARGET="$(mktemp -d -t arcgentic-v2-user-workflow-XXXXXX)"
PROJECT="$TARGET/todo-cli"
mkdir -p "$PROJECT"

STATE="$PROJECT/.agentic-rounds/state.yaml"
CLI=(python -m arcgentic.cli)

cd "$ROOT"
bash scripts/state/init.sh \
  --project-root "$PROJECT" \
  --project-name "todo-cli" \
  --round-naming "R<n>"

cd "$ROOT/toolkit"

python - "$STATE" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
state = yaml.safe_load(path.read_text(encoding="utf-8"))
state["current_round"]["id"] = "R1"
state["current_round"]["state"] = "planning"
state["project"]["arcgentic_v2"] = {
    "host": "codex",
    "mode": "multi-session-subthread",
    "role_sessions": {},
}
path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
PY

"${CLI[@]}" v2-session-plan --state "$STATE" --host codex > "$TARGET/01-plan.json"

python - "$TARGET/01-plan.json" <<'PY'
from pathlib import Path
import json
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["next_role"] == "planner"
assert [action["title"] for action in payload["actions"]] == [
    "Orchestrator",
    "Planner",
    "Developer",
    "Auditor",
]
PY

for role in orchestrator planner developer auditor; do
  "${CLI[@]}" v2-record-session \
    --state "$STATE" \
    --host codex \
    --role "$role" \
    --thread-id "codex-${role}-thread" > "$TARGET/record-$role.json"
done

"${CLI[@]}" v2-return-signal \
  --state "$STATE" \
  --signal-json '{"role":"planner","status":"planned","round_id":"R1","state":"awaiting_dev_start","artifacts":{"handoff":"docs/plans/R1.md"},"next_recommended_role":"developer"}' \
  > "$TARGET/02-planner-signal.json"

"${CLI[@]}" v2-session-plan --state "$STATE" --host codex > "$TARGET/03-dev-plan.json"

"${CLI[@]}" v2-return-signal \
  --state "$STATE" \
  --signal-json '{"role":"developer","status":"completed","round_id":"R1","state":"awaiting_audit","artifacts":{"self_audit":"docs/audits/R1-self-audit.md"},"next_recommended_role":"auditor"}' \
  > "$TARGET/04-dev-signal.json"

"${CLI[@]}" v2-session-plan --state "$STATE" --host codex > "$TARGET/05-audit-plan.json"

"${CLI[@]}" v2-return-signal \
  --state "$STATE" \
  --signal-json '{"role":"auditor","status":"PASS","round_id":"R1","state":"passed","artifacts":{"verdict":"docs/audits/R1.md"},"next_recommended_role":"planner"}' \
  > "$TARGET/06-auditor-signal.json"

python - "$STATE" <<'PY'
from pathlib import Path
import sys
import yaml

state = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert state["current_round"]["state"] == "passed"
assert state["project"]["arcgentic_v2"]["next_role"] == "planner"
sessions = state["project"]["arcgentic_v2"]["role_sessions"]
assert set(sessions) == {"orchestrator", "planner", "developer", "auditor"}
assert all(session["title"] in {"Orchestrator", "Planner", "Developer", "Auditor"} for session in sessions.values())
assert len(state["current_round"]["state_history"]) >= 3
PY

bash "$ROOT/scripts/state/validate-schema.sh" "$STATE"

echo "target=$PROJECT"
echo "state=$STATE"
echo "result=PASS"
