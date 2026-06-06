# Arcgentic V2 Codex Session Orchestration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Arcgentic V2 core contract and first Codex-native session orchestration slice.

**Architecture:** Add a platform-neutral role-session model first, then expose a Codex host plan that maps fixed Arcgentic roles onto reusable Codex threads. The V2 core must not create new role names per round; round and phase identity live in state and prompts, while thread titles stay `Orchestrator`, `Planner`, `Developer`, and `Auditor`.

**Tech Stack:** Python 3.13, dataclasses, argparse CLI, pytest, mypy strict, ruff.

---

## Scope

This first V2 slice implements Codex-ready session orchestration semantics. It does not implement the Claude Code broker yet. Claude Code support comes later by adding a second host adapter over the same core contract.

## Contract Changes

- Remove `closeout` as a session role.
- Keep `close-round` as an orchestrator-owned mechanical command only.
- Route `needs_fix` and `fix_in_progress` back to `Developer`.
- Use fixed role sessions:
  - `Orchestrator`
  - `Planner`
  - `Developer`
  - `Auditor`
- Keep two modes:
  - `single-session-subagent`
  - `multi-session-subthread`
- First platform target:
  - `codex`
- Future platform target:
  - `claude-code-broker`

## Task 1: V2 Role Session Core Tests

**Files:**
- Create: `toolkit/tests/unit/test_v2_session_orchestration.py`
- Create: `toolkit/src/arcgentic/v2_session_orchestration.py`

**Step 1: Write failing tests**

Add tests for:
- fixed role titles are exactly `Orchestrator`, `Planner`, `Developer`, `Auditor`
- Codex session plan creates missing role sessions but reuses existing thread ids
- `needs_fix` routes to `Developer`
- `passed` routes to `Planner` for phase decision, not to `closeout`
- role return signal JSON round-trips

**Step 2: Run test to verify failure**

Run:

```bash
cd toolkit
python3 -m pytest tests/unit/test_v2_session_orchestration.py -q
```

Expected: FAIL because `arcgentic.v2_session_orchestration` does not exist.

## Task 2: Implement V2 Core

**Files:**
- Modify: `toolkit/src/arcgentic/v2_session_orchestration.py`

**Step 1: Implement dataclasses**

Implement:
- `Role`
- `HostKind`
- `V2Mode`
- `RoleSession`
- `RoleAction`
- `RoleReturnSignal`
- `SessionPlan`

**Step 2: Implement routing**

Implement:
- `fixed_role_title(role)`
- `normalize_role(role)`
- `build_codex_role_session_plan(state)`
- `next_role_for_state(state_name, audit_outcome=None)`
- `role_prompt(role, state)`

**Step 3: Run focused tests**

Run:

```bash
cd toolkit
python3 -m pytest tests/unit/test_v2_session_orchestration.py -q
```

Expected: PASS.

## Task 3: CLI Surface

**Files:**
- Modify: `toolkit/src/arcgentic/cli.py`
- Modify: `toolkit/tests/unit/test_cli.py`

**Step 1: Write failing CLI tests**

Add tests for:
- `arcgentic v2-session-plan --state <state.yaml> --host codex`
- JSON output contains fixed roles and `create_or_reuse` actions
- CLI rejects unsupported host values

**Step 2: Implement parser and dispatch**

Add the `v2-session-plan` subcommand. It should read YAML state and print JSON.

**Step 3: Run focused CLI tests**

Run:

```bash
cd toolkit
python3 -m pytest tests/unit/test_cli.py -q
```

Expected: PASS.

## Task 4: Skill and README Contract Update

**Files:**
- Modify: `skills/orchestrate-round/SKILL.md`
- Modify: `skills/session-mode/SKILL.md`
- Modify: `README.md`

**Step 1: Update orchestrator docs**

State that Codex V2 multi-session mode uses fixed Planner/Developer/Auditor threads controlled by Orchestrator.

**Step 2: Update session-mode docs**

Remove `closeout` from session roles. Keep `close-round` as an orchestrator command.

**Step 3: Update README**

Add a V2 preview section that distinguishes:
- Codex native subthread orchestration
- Claude Code broker-backed orchestration planned later

## Task 5: Verification

Run:

```bash
cd toolkit
python3 -m pytest tests/unit/test_v2_session_orchestration.py tests/unit/test_cli.py -q
python3 -m pytest -q
python3 -m mypy src tests
python3 -m ruff check src tests
```

Also run:

```bash
git diff --check
git status --short
```

Expected:
- All focused tests pass.
- Full toolkit tests pass.
- mypy strict passes.
- ruff passes.
- Only intended V2 files are changed.

## Task 6: Commit and Push

Commit message:

```text
feat(v2): add Codex role-session orchestration core
```

Body must mention:
- Codex V2 fixed role sessions
- closeout removed from session-role model
- Claude Code broker deferred to the next adapter slice
