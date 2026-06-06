# Arcgentic V2 User Workflow Dogfood

Date: 2026-06-06

## Goal

Validate the user-facing V2 workflow after local Codex installation:

1. Install Arcgentic as a local Codex plugin source.
2. Initialize a target project.
3. Generate a V2 Codex fixed-role session plan.
4. Record fixed role sessions.
5. Dispatch one role at a time and put Orchestrator to sleep.
6. Wake Orchestrator only through `RoleReturnSignal`.
7. Route Planner -> Developer -> Auditor through sleep/wake cycles.
8. Validate final state against `schema/state.schema.json`.
9. Run a Codex project-scoped host-thread smoke.

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
- `arcgentic v2-record-session` for fixed role sessions
- `arcgentic v2-dispatch-role` for Orchestrator sleep after dispatch
- `arcgentic v2-return-signal` for Planner, Developer, Auditor
- `scripts/state/validate-schema.sh`

The deterministic workflow now verifies that:

- an active Orchestrator receives exactly one next-role action;
- a sleeping Orchestrator receives no dispatch actions;
- `v2-return-signal` wakes the Orchestrator and clears pending dispatch fields.

## Codex Skill Discovery Fix

Failure observed in a real new-project attempt:

- User prompt: `我想做一个极简 todo CLI。请用 Arcgentic来完成`
- Codex selected `build-feature` instead of Arcgentic.
- The agent saw only the `arcgentic` CLI and tried `arcgentic plan-round-impl`.
- When that failed, it attempted to hand-write "Arcgentic-style" evidence.

Fix:

- Added `skills/arcgentic/SKILL.md` as a natural Codex trigger when the user
  mentions Arcgentic.
- Extended `scripts/install-codex-local.sh` to copy Arcgentic skills into
  `~/.codex/skills`.
- Installed local skill directories:
  - `~/.codex/skills/arcgentic`
  - `~/.codex/skills/arcgentic-using-arcgentic`
  - `~/.codex/skills/arcgentic-codex-thread-orchestration`
  - and the remaining Arcgentic role skills.

The new entry skill explicitly forbids silent fallback to "Arcgentic-style"
hand-written evidence.

Additional fixes from the follow-up trigger test:

- Skill directories are copied, not symlinked, because the Codex skill loader
  may not follow symlinked skill directories during discovery.
- Real Planner / Developer / Auditor threads must use the strongest available
  Codex model. Lightweight/spark models are allowed only for explicit low-cost
  smoke tests.

Validated trigger smoke after reinstall:

- Thread id: `019e9cbb-82db-7820-9a85-241938195a34`
- Project cwd: `/Users/archiesun/Documents/ArcToDo`
- Prompt: `我想做一个极简 todo CLI。请用 Arcgentic来完成。`
- Observed response:

```text
先使用 `arcgentic` skill.
必须创建当前 project 下的 `Planner` / `Developer` / `Auditor` role threads;
Arcgentic skill 明确禁止创建 projectless role threads.
```

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

PASS for deterministic CLI coverage, but the later live Codex workflow exposed
one role-boundary failure that required a V2 fix.

Codex role threads must be created with the current project target, not
projectless targets. `skills/codex-thread-orchestration/SKILL.md` now records
this as a fail-closed rule.

## Live Workflow Regression: Planner Latency Race

Observed threads:

- Orchestrator: `019e9cc1-5e1f-78b2-8dac-f712694a9916`
- Planner: `019e9cc2-acf7-7bf1-9acb-167660953ab2`

Failure:

- Arcgentic skill discovery worked and a project-scoped Planner thread was
  created.
- Planner returned slowly.
- Orchestrator sent one tightening prompt, then continued by writing the plan,
  implementation, audit verdict, and closeout itself.
- Planner eventually returned after the Orchestrator had already advanced the
  round to `awaiting_audit`.
- Planner returned `state: "awaiting_audit"` and
  `next_recommended_role: "auditor"`, skipping Developer.
- Planner also returned extra fields outside the `RoleReturnSignal` contract.

Fix:

- `RoleReturnSignal.from_json()` now rejects extra fields.
- `v2-return-signal` now rejects stale role signals when the current state no
  longer belongs to that role.
- `v2-session-plan` now emits only one next-role action while active, and no
  actions while `orchestrator_status` is `sleeping`.
- `v2-dispatch-role` now records `pending_role`, `pending_thread_id`, and
  `pending_since`, making Orchestrator sleep explicit in state.
- Role-specific routing is enforced:
  - Planner cannot route directly to Auditor.
  - Developer cannot bypass Auditor.
  - Auditor alone can route PASS / NEEDS_FIX / AUDIT_IN_PROGRESS.
- `skills/arcgentic` and `skills/codex-thread-orchestration` now require
  fail-closed timeout handling instead of Orchestrator fallback development.
