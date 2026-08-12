---
name: claude-code-session-broker
description: Use when running Arcgentic V2 in Claude Code and fixed Planner, Developer, and Auditor role sessions must be coordinated through a broker.
---

# claude-code-session-broker

Use this skill for Claude Code V2 parity. Claude Code does not expose the same
Codex thread tools to Arcgentic, so V2 parity is broker-backed: the broker keeps
the same four-role state contract and uses Claude Code subagents, Agent Teams,
hooks, or explicit copy-back depending on what the host supports.

Relevant host capabilities:

- Subagents provide isolated role contexts within a session:
  <https://code.claude.com/docs/en/sub-agents>
- Agent Teams coordinate across separate sessions when enabled:
  <https://code.claude.com/docs/en/agent-teams>
- Hooks can observe stop events and final assistant output:
  <https://code.claude.com/docs/en/hooks>

## Contract

V2 still has exactly five role identities:

- `Orchestrator`
- `Planner`
- `Developer`
- `Test`
- `Auditor`

Do not create round-numbered role identities. Store round identity in state and
prompt payloads.

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

## Hook guidance

When hooks are available, configure stop hooks to extract the role's final
response and pass it back to the orchestrator as context. The hook must not
invent a PASS/NEEDS_FIX outcome. It only transports the role's own
`RoleReturnSignal`.

The bundled hook runtime uses official Claude Code Stop/SubagentStop input
fields, especially `last_assistant_message` and `stop_hook_active`. If the
Orchestrator is sleeping and the role output lacks a valid footer, the hook
blocks once with a corrective reason. If `stop_hook_active` is already true, it
does not block again, preventing hook recursion.

## Fail-closed rules

- If a role returns prose without valid `RoleReturnSignal`, do not advance.
- If the broker cannot identify which role produced a signal, do not advance.
- If the Orchestrator is sleeping, do not dispatch more work until the pending
  role returns.
- If a role tries to rename itself outside the four fixed titles, reject it.
- If Claude Code transport is unavailable, fall back to explicit copy-back
  rather than pretending automation succeeded.
