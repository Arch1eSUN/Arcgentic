# Claude Code V2 Native-Tooling Broker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `skills/claude-code-session-broker/SKILL.md` a concrete "tier 0" dispatch procedure using `Agent`/`SendMessage`/`ListAgents`, demote the existing hook-backed broker to a documented fallback, prove the new procedure works with a real dogfood run, and update README's status line to match what was actually verified.

**Architecture:** This is a documentation-and-verification plan, not a code plan. `toolkit/src/arcgentic/v2_session_orchestration.py`'s `build_role_session_plan()`/`role_prompt()` already produce host-agnostic dispatch data (`SessionPlan.actions[].prompt` is the complete, ready-to-send role prompt, footer format included) — nothing there changes. The only gap is skill-level instructions for which concrete tool call to wrap that data in, and proof it actually works end to end.

**Tech Stack:** Markdown (SKILL.md/README.md edits), a real Claude session dogfood run (no pytest — this cannot be unit tested).

## Global Constraints

- No changes to `toolkit/src/arcgentic/v2_session_orchestration.py`, `cli.py`, or `claude_code_broker.py` — the existing CLI surface (`v2-session-plan`, `v2-record-session`, `v2-dispatch-role`, `v2-return-signal`) is unchanged and sufficient.
- The dogfood run must NOT touch this repo's own `.agentic-rounds/state.yaml` — that file tracks arcgentic's real round history (currently at round `R3-v1-prepublish-fix`, closed) and must not be polluted with throwaway test data. Run the dogfood test against a scratch project in a temp directory instead.
- README's status line may only claim "verified" for whichever V2 mode (`single-session-subagent` and/or `multi-session-subthread`) the dogfood run actually exercised — do not generalize beyond what was tested.
- The hook-backed broker's existing test suite (`toolkit/tests/unit/test_claude_code_broker.py`) and Python code must be untouched and still pass.

---

### Task 1: Rewrite `skills/claude-code-session-broker/SKILL.md`'s dispatch procedure

**Files:**
- Modify: `skills/claude-code-session-broker/SKILL.md` (entire "Broker priority" and "Procedure" sections; frontmatter/Contract sections stay as-is)

**Interfaces:**
- Consumes: existing CLI commands, unchanged — `arcgentic v2-session-plan --state <path> --host claude-code-broker --user-request '<text>'` (returns JSON with `actions[0].{role,title,kind,prompt,thread_id,target}`, `orchestrator_status`, `pending_role`), `arcgentic v2-record-session --state <path> --host claude-code-broker --role <role> --thread-id <id>`, `arcgentic v2-dispatch-role --state <path> --host claude-code-broker --role <role> --thread-id <id>`, `arcgentic v2-return-signal --state <path> --signal-json '<json>'` (or `--signal-text`).
- Produces: the rewritten skill text later tasks' dogfood run follows literally — Task 2's dogfood run must be executable by reading only this file, not by inferring anything not written here.

- [ ] **Step 1: Replace the "Broker priority" section**

In `skills/claude-code-session-broker/SKILL.md`, find the section starting `## Broker priority` (currently a 4-item numbered list: "1. Hook-backed broker... 2. Agent Teams... 3. Background subagents + hooks... 4. Explicit copy-back"). Replace the entire section with:

```markdown
## Broker priority

Use the strongest available transport, checked in this order:

1. **Native tooling (tier 0)** — if this session's own tool list includes
   `Agent`, `SendMessage`, and `ListAgents`, use them directly (see
   "Procedure — tier 0" below). Dispatch is synchronous for a foreground
   `Agent` call (you get the role's output the moment the call returns —
   no external event to wait for) or notification-driven for a background
   `Agent` call (a task-notification arrives with the role's output when
   it finishes). Either way, `Agent`'s result always carries a resumable
   `agentId` — record it as the broker `thread-id` in both cases.
2. **Hook-backed broker (fallback)** — use when tier 0's three tools are
   not present in this session (see "Procedure — hook fallback" below).
3. **Explicit copy-back (last resort)** — when neither of the above is
   available: the role session returns `RoleReturnSignal` in its own
   output, and a human or the orchestrator manually runs
   `arcgentic v2-return-signal` with that JSON. No automation attempts
   this on its own; do not pretend it succeeded silently.

All three transports write the same state shape via the same CLI
commands (`v2-session-plan`, `v2-record-session`, `v2-dispatch-role`,
`v2-return-signal`) — only how the role's prompt gets delivered and its
output gets collected differs.
```

- [ ] **Step 2: Replace the "Procedure" section**

Find the section starting `## Procedure` (the 8-step numbered list starting "1. Install project-local Claude Code hooks once..."). Replace the entire section with:

```markdown
## Procedure — tier 0 (native tooling)

Check once per session, before dispatching anything: does your own tool
list include `Agent`, `SendMessage`, and `ListAgents`? If yes, use this
procedure. If no, skip to "Procedure — hook fallback" below.

1. Get the dispatch plan:

   ```bash
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --user-request '<current user request>'
   ```

2. If the JSON's `orchestrator_status` is `sleeping`, stop immediately —
   a role is already dispatched and pending; do not dispatch another.

3. If `orchestrator_status` is `active`, read `actions[0]`. Its `prompt`
   field is the complete, ready-to-send role prompt (it already contains
   the `arcgentic-role-return` footer instructions — do not edit it, do
   not add or remove content).

4. Dispatch:
   - `single-session-subagent` mode: call the `Agent` tool with
     `prompt` = `actions[0].prompt`, `run_in_background: false`
     (foreground — you get the result directly in this same turn), and
     `subagent_type` matched to the role (`developer`/`auditor`/etc. if a
     matching type exists in your environment, otherwise
     `general-purpose`).
   - `multi-session-subthread` mode: call `Agent` with the same `prompt`
     but `run_in_background: true`. Then immediately record the dispatch
     and end your turn (steps 5-6 below) — do not wait inline for a
     background call.

5. Record the session, using the `agentId` `Agent` returned as the
   broker `thread-id`:

   ```bash
   arcgentic v2-record-session \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --role <planner|developer|test|auditor> \
     --thread-id <agentId>
   ```

6. Put the Orchestrator to sleep and end your turn:

   ```bash
   arcgentic v2-dispatch-role \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --role <planner|developer|test|auditor> \
     --thread-id <agentId>
   ```

7. Collect the role's output:
   - Foreground `Agent` call: its return value IS the role's output —
     continue directly to step 8 in the same turn, no waiting.
   - Background `Agent` call: wait for the task-notification. When it
     arrives, its content is the role's output. Do not poll `ListAgents`
     for completion — the notification is the completion signal.

8. Validate the output contains exactly one
   ` ```arcgentic-role-return ... ``` ` fenced JSON footer (or the
   `ARCGENTIC_ROLE_RETURN ... END_ARCGENTIC_ROLE_RETURN` marker form).
   If it's missing or malformed, use `SendMessage` to resume the same
   agent (by its `agentId`) with a corrective instruction: "Your last
   response was missing the required `arcgentic-role-return` footer.
   Re-send your summary with exactly one such footer, formatted as
   instructed." Repeat step 8 with the resumed agent's reply. This is
   the same fail-closed contract the hook fallback enforces via
   `decision: block` — here it's enforced by you, the orchestrator,
   checking directly, since there is no external hook watching this
   session.

9. Record the signal, which wakes the Orchestrator:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-json '<the footer JSON from step 8>'
   ```

10. Go back to step 1 and dispatch the next role.

## Procedure — hook fallback

Use this procedure only when tier 0's `Agent`/`SendMessage`/`ListAgents`
are not available in this session.

1. Install project-local Claude Code hooks once:

   ```bash
   arcgentic claude-code-broker install-hooks \
     --settings .claude/settings.local.json \
     --state .agentic-rounds/state.yaml
   ```

   The installed Stop/SubagentStop hook calls:

   ```bash
   arcgentic claude-code-broker handle-stop \
     --state .agentic-rounds/state.yaml
   ```

   The hook reads Claude Code's `last_assistant_message`, extracts the
   `arcgentic-role-return` footer, runs the same V2 return validation,
   updates `.agentic-rounds/state.yaml`, and writes a broker inbox
   record under `.agentic-rounds/claude-code-broker/inbox/`.

2. Initialize or read V2 host state:

   ```bash
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --user-request '<current user request>'
   ```

3. If `orchestrator_status` is `sleeping`, stop immediately. The broker
   is waiting for `pending_role`; do not dispatch another role.

4. If `orchestrator_status` is `active`, create or resume only the
   single role context in `actions`, then record its broker id:

   ```bash
   arcgentic v2-record-session \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --role <planner|developer|test|auditor> \
     --thread-id <broker-session-id>
   ```

5. Inject only that role's prompt. The developer does not receive
   auditor reasoning. The auditor does not receive developer chat
   transcript. The planner owns phase decisions.

6. After injecting the role prompt, put the Orchestrator to sleep and
   end the Orchestrator turn:

   ```bash
   arcgentic v2-dispatch-role \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --role <planner|developer|test|auditor> \
     --thread-id <broker-session-id>
   ```

7. Require every role turn to end with `RoleReturnSignal` JSON.

8. Record the signal. This wakes the Orchestrator and clears the
   pending dispatch:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-json '<RoleReturnSignal JSON>'
   ```

9. Re-run `v2-session-plan --host claude-code-broker` and dispatch the
   next role.
```

Everything from `## Hook guidance` onward in the current file stays exactly as-is (it documents the hook's own behavior, still accurate for the fallback path) — do not touch it.

- [ ] **Step 3: Self-consistency check**

Read the full rewritten file once. Confirm: every CLI command mentioned (`v2-session-plan`, `v2-record-session`, `v2-dispatch-role`, `v2-return-signal`, `claude-code-broker install-hooks`, `claude-code-broker handle-stop`) actually exists — cross-check each against `toolkit/src/arcgentic/cli.py`'s subcommand list:

Run: `grep -n 'subparsers.add_parser(' toolkit/src/arcgentic/cli.py`
Expected: `v2-session-plan`, `v2-record-session`, `v2-dispatch-role`, `v2-return-signal`, `claude-code-broker` all appear in the output.

- [ ] **Step 4: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add skills/claude-code-session-broker/SKILL.md
git commit -m "feat(skills): add tier-0 native-tooling dispatch to claude-code-session-broker

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Live dogfood verification of the tier-0 procedure

**Files:**
- Create: a scratch project directory (NOT inside the arcgentic repo — see step 1)
- Create: `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md` (inside the arcgentic repo — this is the permanent record)

**Interfaces:** none — this task drives real tool calls (`Agent`, `SendMessage`), not code.

**This task cannot be delegated to a subagent that lacks `Agent`/`SendMessage`/`ListAgents` itself.** Whoever executes this task (the controller session, or a dispatched subagent that has those three tools available to it) must literally follow Task 1's new tier-0 procedure by hand, in real time, and record exactly what happened — not simulate or describe what would happen.

- [ ] **Step 1: Set up an isolated scratch project**

Create a throwaway project directory outside the arcgentic repo (use your session's scratchpad directory if one is designated, otherwise any temp directory) — e.g.:

```bash
mkdir -p /tmp/arcgentic-dogfood-gate3/toy-project
cd /tmp/arcgentic-dogfood-gate3/toy-project
git init -q
echo "# Toy project for arcgentic Claude Code V2 dogfood gate 3" > README.md
git add README.md
git commit -q -m "init toy project"
```

This is the project the dogfood round runs against — never the arcgentic repo's own `.agentic-rounds/state.yaml`.

- [ ] **Step 2: Bootstrap state.yaml for V2 in the toy project**

```bash
mkdir -p .agentic-rounds
cat > .agentic-rounds/state.yaml <<'EOF'
schema_version: '0.1'
project:
  name: toy-project
  root: /tmp/arcgentic-dogfood-gate3/toy-project
  round_naming: R<n>
  paths:
    plans_dir: docs/plans
    audits_dir: docs/audits
  arcgentic_v2:
    host: claude-code-broker
    mode: single-session-subagent
    role_sessions: {}
current_round:
  id: R1
  state: intake
  state_history: []
states: {}
EOF
```

(`mode: single-session-subagent` is pre-set here to skip the interactive mode-selection step in `skills/arcgentic/SKILL.md` — this dogfood run is scoped to proving the tier-0 dispatch mechanics, not re-testing mode selection, which is unrelated to this plan.)

- [ ] **Step 3: Run the tier-0 procedure for exactly one role (Planner)**

Follow Task 1's new "Procedure — tier 0" section literally, using `.agentic-rounds/state.yaml` inside the toy project (not the arcgentic repo), with this as the user request: `"Add a one-line CONTRIBUTING.md note saying pull requests are welcome."` (deliberately trivial — the point is proving the dispatch mechanism works, not producing a real plan).

Run step 1 of the procedure:
```bash
cd /tmp/arcgentic-dogfood-gate3/toy-project
arcgentic v2-session-plan \
  --state .agentic-rounds/state.yaml \
  --host claude-code-broker \
  --user-request 'Add a one-line CONTRIBUTING.md note saying pull requests are welcome.'
```
Record the full JSON output — this goes into RESULT.md verbatim.

Then dispatch a foreground `Agent` call with `prompt` = the JSON's `actions[0].prompt`, `run_in_background: false`, `subagent_type: "general-purpose"`. Record the returned `agentId` and the full response text.

Then run steps 5, 6, 8, 9 of the tier-0 procedure exactly as written (record-session, dispatch-role, validate the footer, return-signal) against the toy project's state.yaml. Record every command run and its exact output.

- [ ] **Step 4: Write `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`**

Back in the arcgentic repo:

```bash
mkdir -p "/Users/archiesun/Desktop/Arc Studio/arcgentic/tests/dogfood/gate-3-claude-code-native-broker"
```

Write a RESULT.md file with these exact sections (fill each with the REAL commands/output/timestamps from Steps 1-3 — no placeholder text, no fabricated success):

```markdown
# Dogfood Gate 3 — Claude Code V2 Native-Tooling Broker (tier 0)

**Date:** <real date>
**Mode tested:** single-session-subagent (foreground `Agent` dispatch only — `multi-session-subthread`/background dispatch was NOT tested in this gate; do not claim it was)
**Scratch project:** /tmp/arcgentic-dogfood-gate3/toy-project (outside the arcgentic repo; not committed)

## What was tested

Followed `skills/claude-code-session-broker/SKILL.md`'s tier-0 procedure by hand,
end to end, for one Planner dispatch.

## Commands run and real output

<paste every command from Step 3 and its actual output verbatim, in order —
v2-session-plan output, the Agent tool call parameters and its returned agentId
and response text, v2-record-session output, v2-dispatch-role output, the footer
validation result, v2-return-signal output>

## Outcome

- [ ] `v2-session-plan` returned a valid dispatch plan with `actions[0].prompt`
- [ ] Foreground `Agent` call returned a response containing a valid
      `arcgentic-role-return` footer on the first attempt (or: required one
      `SendMessage` correction — record which)
- [ ] `v2-record-session` succeeded
- [ ] `v2-dispatch-role` succeeded
- [ ] `v2-return-signal` accepted the footer JSON and advanced
      `current_round.state` correctly

## Verdict

PASS | PARTIAL | FAIL — <one sentence why>
```

If any step failed, record the failure honestly as FAIL or PARTIAL — do not edit the plan to make it look like it passed. A failed gate is a real, useful finding; a fabricated pass is not.

- [ ] **Step 5: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add tests/dogfood/gate-3-claude-code-native-broker/RESULT.md
git commit -m "test(dogfood): verify tier-0 native-tooling broker dispatch (gate 3)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Update README's Claude Code V2 status line

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md` (keep in sync — the repo's own convention, per the existing TODO note in CLAUDE.md about README.zh-CN lagging alpha.1; do not let this change introduce a fresh English/Chinese drift)

**Interfaces:**
- Consumes: Task 2's RESULT.md verdict — this task's wording depends entirely on what Task 2 actually found. If Task 2's verdict was PARTIAL or FAIL, this task's Step 1 changes accordingly (see below) — do not proceed with the "PASS" wording if Task 2 didn't pass.

- [ ] **Step 1: Read Task 2's verdict before writing anything**

Run: `grep -A2 "## Verdict" "/Users/archiesun/Desktop/Arc Studio/arcgentic/tests/dogfood/gate-3-claude-code-native-broker/RESULT.md"`

If the verdict is PASS: proceed to Step 2 with the wording below.
If the verdict is PARTIAL or FAIL: do not claim "verified" in README. Instead, update the status line to reference the new tier-0 procedure as available-but-only-partially-verified, quoting the specific gap from RESULT.md's verdict line, and stop — do not fabricate a stronger claim than the evidence supports. Report this outcome rather than silently downgrading your own task to "done."

- [ ] **Step 2 (only if Task 2's verdict was PASS): Update the status table**

In `README.md`, find the "Platform status" table:

```markdown
| Platform | V2 status | Verification |
|---|---|---|
| **Codex** | Complete V2 | Verified in a real Codex project workflow, including automatic Orchestrator thread setup and role-thread dispatch. |
| **Claude Code** | Complete V2 experimental | Not yet verified in a real Claude Code session. |
```

Replace the Claude Code row with:

```markdown
| **Claude Code** | Complete V2 | Verified in a real Claude Code session for `single-session-subagent` mode via the native-tooling (`Agent`/`SendMessage`/`ListAgents`) tier-0 broker path — see `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`. `multi-session-subthread` mode and the hook-backed fallback path remain unverified by this gate. |
```

Also find and update the paragraph below the table that currently reads (or similar): "Claude Code support is available as an experimental version and should be treated as a real workflow candidate, not as proven production behavior yet." — soften this to reflect that `single-session-subagent` mode specifically now has dogfood evidence, while `multi-session-subthread` and the hook fallback do not yet.

Do NOT remove the caveat entirely — only `single-session-subagent` mode via tier 0 was tested; the rest of the platform-status nuance (multi-session-subthread, hook fallback) genuinely remains unverified and the README must keep saying so.

- [ ] **Step 3: Apply the same change to `README.zh-CN.md`**

Find the equivalent table/paragraph in `README.zh-CN.md` (search for "Claude Code" and the same status-table structure) and apply an equivalent Chinese-language edit — same substance (single-session-subagent verified via tier-0, multi-session-subthread and hook fallback still not), matching this repo's existing bilingual-parity convention.

- [ ] **Step 4: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add README.md README.zh-CN.md
git commit -m "docs: update Claude Code V2 status after tier-0 dogfood gate 3

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
