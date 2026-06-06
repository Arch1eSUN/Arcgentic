# Arcgentic V2 User Workflow Dogfood

Date: 2026-06-06

## Goal

Validate the user-facing V2 workflow after local Codex installation:

1. Install Arcgentic as a local Codex plugin source.
2. Initialize a target project.
3. Generate a V2 Codex fixed-role session plan.
4. Record fixed role sessions.
5. Route Planner -> Developer -> Auditor through `RoleReturnSignal`.
6. Validate final state against `schema/state.schema.json`.
7. Run a Codex project-scoped host-thread smoke.

## Local Codex Install

Command:

```bash
bash scripts/install-codex-local.sh --plugin-root .
```

Observed output:

```text
Plugin validation passed: /Users/archiesun/Desktop/Arc Studio/arcgentic
arcgentic Codex local plugin installed
plugin_link=/Users/archiesun/plugins/arcgentic
marketplace=/Users/archiesun/plugins/.agents/plugins/marketplace.json
```

## Deterministic User Workflow Target

Target: temporary `todo-cli` project created by:

```bash
bash tests/dogfood/v2-user-workflow/run.sh
```

Observed output:

```text
valid: <tmp>/todo-cli/.agentic-rounds/state.yaml
target=<tmp>/todo-cli
state=<tmp>/todo-cli/.agentic-rounds/state.yaml
result=PASS
```

Workflow covered:

- `scripts/state/init.sh`
- `arcgentic v2-session-plan --host codex`
- `arcgentic v2-record-session` for all four fixed roles
- `arcgentic v2-return-signal` for Planner, Developer, Auditor
- `scripts/state/validate-schema.sh`

## Codex Project-Scoped Host Smoke

Invalid attempt:

- Projectless Planner / Developer / Auditor threads were created first.
- This is not a valid Arcgentic V2 workflow because role sessions must share the
  current project workspace.
- Those projectless threads were archived.

Valid project-scoped threads:

| Role | Thread id | Title | cwd |
|---|---|---|---|
| Orchestrator | `019e9313-4575-7723-97c0-a6a26e1afe82` | `Orchestrator` | `/Users/archiesun/Desktop/Arc Studio/arcgentic` |
| Planner | `019e9c96-2120-78e2-af4f-b53b813a0496` | `Planner` | `/Users/archiesun/Desktop/Arc Studio/arcgentic` |
| Developer | `019e9c96-8005-7a51-a81c-cbbf04655ca0` | `Developer` | `/Users/archiesun/Desktop/Arc Studio/arcgentic` |
| Auditor | `019e9c96-bf73-76b1-8044-0e561cc3d75d` | `Auditor` | `/Users/archiesun/Desktop/Arc Studio/arcgentic` |

Observed role returns:

```json
{"role":"planner","status":"planned","round_id":"R1","state":"awaiting_dev_start","artifacts":{"handoff":"tests/dogfood/v2-user-workflow/R1-handoff.md"},"next_recommended_role":"developer"}
{"role":"developer","status":"completed","round_id":"R1","state":"awaiting_audit","artifacts":{"self_audit":"tests/dogfood/v2-user-workflow/R1-self-audit.md"},"next_recommended_role":"auditor"}
{"role":"auditor","status":"PASS","round_id":"R1","state":"passed","artifacts":{"verdict":"tests/dogfood/v2-user-workflow/R1-verdict.md"},"next_recommended_role":"planner"}
```

## Result

PASS with one adapter lesson:

Codex role threads must be created with the current project target, not
projectless targets. `skills/codex-thread-orchestration/SKILL.md` now records
this as a fail-closed rule.
