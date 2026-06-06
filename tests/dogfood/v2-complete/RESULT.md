# Arcgentic V2 Complete Dogfood Result

Date: 2026-06-06

## Scope

This dogfood validates the V2 fixed-role orchestration contract:

- Codex host mode emits fixed-role thread actions.
- Claude Code broker mode emits the same fixed-role action model.
- Role thread ids persist into `.agentic-rounds/state.yaml`.
- Role return signals persist into state and route the next role.
- `close-round` remains an orchestrator command, not a session role.

## Commands

```bash
cd toolkit
python -m pytest tests/unit/test_cli.py tests/unit/test_v2_session_orchestration.py -q
python -m pytest -q
python -m mypy src tests
python -m ruff check src tests
cd ..
python -m json.tool schema/state.schema.json >/dev/null
for f in scripts/state/*.test.sh; do bash "$f"; done
git diff --check
```

## Expected Contract

Fixed role titles:

- `Orchestrator`
- `Planner`
- `Developer`
- `Auditor`

Routing:

- `needs_fix` / `fix_in_progress` -> `Developer`
- `awaiting_audit` / `audit_in_progress` -> `Auditor`
- `passed` -> `Planner`

Host support:

- `codex`: native thread orchestration skill.
- `claude-code-broker`: broker-backed parity skill.

## Result

PASS.

Observed verification:

- `python -m pytest -q` -> `337 passed`
- `python -m mypy src tests` -> no issues
- `python -m ruff check src tests` -> all checks passed
- `python -m json.tool` over manifests and state schema -> pass
- `scripts/state/*.test.sh` -> pass
- `git diff --check` -> pass

Observed V2 CLI flow:

```bash
arcgentic v2-session-plan --state <tmp>/state.yaml --host codex
arcgentic v2-record-session --state <tmp>/state.yaml --host codex --role auditor --thread-id audit-thread-1
arcgentic v2-return-signal --state <tmp>/state.yaml --signal-json '{"role":"auditor","status":"NEEDS_FIX","round_id":"R1","state":"needs_fix","artifacts":{"verdict":"docs/audits/R1.md"},"next_recommended_role":"developer"}'
```

Result:

```json
{
  "next_role": "developer",
  "recorded": true
}
```

State evidence:

```yaml
thread_id: audit-thread-1
last_signal:
next_role: developer
```
