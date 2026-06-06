#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TARGET="$(mktemp -d -t arcgentic-v2-user-workflow-XXXXXX)"
PROJECT="$TARGET/arctest"
mkdir -p "$PROJECT"
STATE="$PROJECT/.agentic-rounds/state.yaml"
CLI=(python -m arcgentic.cli)

cd "$ROOT"
bash scripts/state/init.sh \
  --project-root "$PROJECT" \
  --project-name "ArcTest" \
  --round-naming "R<n>"

cd "$ROOT/toolkit"

python - "$STATE" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
state = yaml.safe_load(path.read_text(encoding="utf-8"))
state["current_round"]["id"] = "R1"
state["project"]["arcgentic_v2"] = {
    "host": "codex",
    "mode": "multi-session-subthread",
    "orchestrator_status": "active",
    "role_sessions": {},
}
path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
PY

"${CLI[@]}" v2-record-session \
  --state "$STATE" \
  --host codex \
  --role orchestrator \
  --thread-id "codex-orchestrator-thread" > "$TARGET/record-orchestrator.json"

"${CLI[@]}" v2-session-plan \
  --state "$STATE" \
  --host codex \
  --user-request "我想做一个很小的命令行工具，用来计算几个人聚餐后的 AA 分账和最少转账方案。请用 Arcgentic 来完成。" \
  > "$TARGET/01-plan.json"

python - "$TARGET/01-plan.json" <<'PY'
from pathlib import Path
import json
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["next_role"] == "planner"
assert payload["orchestrator_status"] == "active"
assert [action["title"] for action in payload["actions"]] == ["Planner"]
assert "Current user request: 我想做一个很小的命令行工具" in payload["actions"][0]["prompt"]
assert "Use natural language for your role-owned output" in payload["actions"][0]["prompt"]
assert "send a message to Orchestrator thread codex-orchestrator-thread" in payload["actions"][0]["prompt"]
PY

"${CLI[@]}" v2-record-session \
  --state "$STATE" \
  --host codex \
  --role planner \
  --thread-id "codex-planner-thread" > "$TARGET/record-planner.json"

"${CLI[@]}" v2-dispatch-role \
  --state "$STATE" \
  --host codex \
  --role planner \
  --thread-id "codex-planner-thread" > "$TARGET/dispatch-planner.json"

"${CLI[@]}" v2-session-plan \
  --state "$STATE" \
  --host codex \
  --user-request "我想做一个很小的命令行工具，用来计算几个人聚餐后的 AA 分账和最少转账方案。请用 Arcgentic 来完成。" \
  > "$TARGET/01-sleeping-plan.json"

python - "$TARGET/01-sleeping-plan.json" <<'PY'
from pathlib import Path
import json
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["orchestrator_status"] == "sleeping"
assert payload["pending_role"] == "planner"
assert payload["actions"] == []
PY

"${CLI[@]}" v2-return-signal \
  --state "$STATE" \
  --signal-text 'Planner completed a natural-language plan for the AA split CLI.

```arcgentic-role-return
{"role":"planner","status":"planned","round_id":"R1","state":"awaiting_dev_start","artifacts":{"handoff":"docs/plans/R1-expense-splitter.md"},"next_recommended_role":"developer"}
```' \
  > "$TARGET/02-planner-signal.json"

"${CLI[@]}" v2-session-plan \
  --state "$STATE" \
  --host codex \
  --user-request "我想做一个很小的命令行工具，用来计算几个人聚餐后的 AA 分账和最少转账方案。请用 Arcgentic 来完成。" \
  > "$TARGET/03-dev-plan.json"

"${CLI[@]}" v2-record-session \
  --state "$STATE" \
  --host codex \
  --role developer \
  --thread-id "codex-developer-thread" > "$TARGET/record-developer.json"

"${CLI[@]}" v2-dispatch-role \
  --state "$STATE" \
  --host codex \
  --role developer \
  --thread-id "codex-developer-thread" > "$TARGET/dispatch-developer.json"

"${CLI[@]}" v2-return-signal \
  --state "$STATE" \
  --signal-text 'Developer completed implementation, tests, and self-audit.

ARCGENTIC_ROLE_RETURN
{"role":"developer","status":"completed","round_id":"R1","state":"awaiting_audit","artifacts":{"self_audit":"docs/audits/R1-self-audit.md"},"next_recommended_role":"auditor"}
END_ARCGENTIC_ROLE_RETURN' \
  > "$TARGET/04-dev-signal.json"

"${CLI[@]}" v2-session-plan \
  --state "$STATE" \
  --host codex \
  --user-request "我想做一个很小的命令行工具，用来计算几个人聚餐后的 AA 分账和最少转账方案。请用 Arcgentic 来完成。" \
  > "$TARGET/05-audit-plan.json"

"${CLI[@]}" v2-record-session \
  --state "$STATE" \
  --host codex \
  --role auditor \
  --thread-id "codex-auditor-thread" > "$TARGET/record-auditor.json"

"${CLI[@]}" v2-dispatch-role \
  --state "$STATE" \
  --host codex \
  --role auditor \
  --thread-id "codex-auditor-thread" > "$TARGET/dispatch-auditor.json"

"${CLI[@]}" v2-return-signal \
  --state "$STATE" \
  --signal-text 'Auditor completed an external audit verdict and found PASS.

```arcgentic-role-return
{"role":"auditor","status":"PASS","round_id":"R1","state":"passed","artifacts":{"verdict":"docs/audits/R1.md"},"next_recommended_role":"planner"}
```' \
  > "$TARGET/06-auditor-signal.json"

python - "$STATE" <<'PY'
from pathlib import Path
import sys
import yaml

state = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert state["current_round"]["state"] == "passed"
v2 = state["project"]["arcgentic_v2"]
assert v2["next_role"] == "planner"
assert v2["orchestrator_status"] == "active"
assert "pending_role" not in v2
assert "pending_thread_id" not in v2
sessions = v2["role_sessions"]
assert set(sessions) == {"orchestrator", "planner", "developer", "auditor"}
assert all(session["title"] in {"Orchestrator", "Planner", "Developer", "Auditor"} for session in sessions.values())
assert len(state["current_round"]["state_history"]) >= 3
PY

bash "$ROOT/scripts/state/validate-schema.sh" "$STATE"

echo "target=$PROJECT"
echo "state=$STATE"
echo "result=PASS"
