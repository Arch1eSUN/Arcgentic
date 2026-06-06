# Arcgentic V2 Complete Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete Arcgentic V2 as a fixed-role orchestration system for Codex and a broker-backed parity system for Claude Code.

**Architecture:** Keep Python as the control plane. V2 state and routing live in `toolkit/src/arcgentic/v2_session_orchestration.py`, host-specific behavior is expressed through CLI JSON plans and markdown skills, and `.agentic-rounds/state.yaml` is the durable memory for fixed role sessions.

**Tech Stack:** Python 3.13, dataclasses, argparse, PyYAML, jsonschema, pytest, mypy strict, ruff, Bash gates, Markdown skills.

---

## Contract

V2 has exactly four role sessions:

- `Orchestrator`
- `Planner`
- `Developer`
- `Auditor`

No role session may be named by round id. `close-round` remains an orchestrator-owned mechanical command after anchored PASS.

## Host Targets

- `codex`: native host-thread orchestration. The current thread is `Orchestrator`; Codex thread tools create, rename, send to, and read fixed role threads.
- `claude-code-broker`: broker-backed parity. Claude Code uses subagents / agent teams / hooks where available, but Arcgentic stores the same four role identities and return-signal protocol in state.

## Task 1: V2 State Persistence Tests

**Files:**
- Modify: `toolkit/tests/unit/test_v2_session_orchestration.py`

**Step 1: Add tests**

Add tests for:

- `record_role_session()` creates `project.arcgentic_v2.role_sessions.<role>`
- recording a role keeps fixed titles and updates `updated_at`
- `apply_role_return_signal()` stores `last_signal`
- unsupported roles fail closed

**Step 2: Verify failure**

Run:

```bash
cd toolkit
python -m pytest tests/unit/test_v2_session_orchestration.py -q
```

Expected: FAIL because persistence functions do not exist.

## Task 2: Implement V2 State Persistence

**Files:**
- Modify: `toolkit/src/arcgentic/v2_session_orchestration.py`

**Step 1: Implement dataclasses and helpers**

Add:

- `RoleSession`
- `record_role_session(state, role, thread_id, title=None, host="codex")`
- `apply_role_return_signal(state, signal)`
- `load_state_file(path)`
- `write_state_file(path, state)`

**Step 2: Run focused tests**

Run:

```bash
cd toolkit
python -m pytest tests/unit/test_v2_session_orchestration.py -q
```

Expected: PASS.

## Task 3: V2 CLI Commands

**Files:**
- Modify: `toolkit/src/arcgentic/cli.py`
- Modify: `toolkit/tests/unit/test_cli.py`

**Step 1: Add failing tests**

Add tests for:

- `arcgentic v2-record-session --state <state> --role developer --thread-id <id>`
- `arcgentic v2-dispatch-role --state <state> --role developer --thread-id <id>`
- `arcgentic v2-return-signal --state <state> --signal-json <json>`
- `arcgentic v2-session-plan --host claude-code-broker` emits one next-role action
  with broker host metadata when active, and no actions while sleeping

**Step 2: Implement CLI dispatch**

Implement the new commands using V2 core helpers.

**Step 3: Run tests**

```bash
cd toolkit
python -m pytest tests/unit/test_cli.py tests/unit/test_v2_session_orchestration.py -q
```

Expected: PASS.

## Task 4: State Schema

**Files:**
- Modify: `schema/state.schema.json`

**Step 1: Add `project.arcgentic_v2`**

Allow:

- `host`: `codex` or `claude-code-broker`
- `mode`: `single-session-subagent` or `multi-session-subthread`
- `orchestrator_status`: `active` or `sleeping`
- `pending_role`, `pending_thread_id`, `pending_since`: the in-flight dispatch
  that must return before Orchestrator can continue
- `role_sessions`: fixed role keys with `thread_id`, `title`, `host`, `updated_at`
- `last_signal`: role return-signal snapshot

**Step 2: Run schema tests**

```bash
for f in scripts/state/*.test.sh; do bash "$f"; done
```

Expected: PASS.

## Task 5: Codex Host Orchestration Skill

**Files:**
- Create: `skills/codex-thread-orchestration/SKILL.md`
- Modify: `plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.claude-plugin/plugin.json`

**Step 1: Add skill**

Document the Codex host procedure:

1. Current thread is `Orchestrator`.
2. Run `arcgentic v2-session-plan --host codex`.
3. If sleeping, stop until the pending role returns.
4. If active, dispatch exactly one next-role action.
5. Run `v2-dispatch-role` and end the Orchestrator turn.
6. Read role result only on the next Orchestrator turn and require
   `RoleReturnSignal`.
7. Run `v2-return-signal` to wake the Orchestrator and calculate the next role.

**Step 2: Register skill**

Add the skill to manifests.

## Task 6: Claude Code Broker Skill

**Files:**
- Create: `skills/claude-code-session-broker/SKILL.md`
- Modify: `plugin.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `README.md`

**Step 1: Add skill**

Document broker-backed parity:

- Use fixed roles.
- Prefer Claude Code Agent Teams when available.
- Use hooks to capture stop output / final response when available.
- Fall back to explicit `RoleReturnSignal` copy-back.
- Persist all role IDs / aliases into `.agentic-rounds/state.yaml`.

**Step 2: Register skill**

Add the skill to manifests.

## Task 7: Dogfood Artifact

**Files:**
- Create: `tests/dogfood/v2-complete/RESULT.md`

Record:

- CLI plan output shape
- session record persistence
- return signal routing
- Codex complete / Claude Code broker-backed status
- verification commands

## Task 8: Verification and Commit

Run:

```bash
cd toolkit
python -m pytest -q
python -m mypy src tests
python -m ruff check src tests
cd ..
git diff --check
```

Commit:

```bash
git add <intended files>
git commit -m "feat(v2): complete fixed-role session orchestration"
git push origin main
```
