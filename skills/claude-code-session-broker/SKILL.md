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

V2 still has exactly four role identities:

- `Orchestrator`
- `Planner`
- `Developer`
- `Auditor`

Do not create round-numbered role identities. Store round identity in state and
prompt payloads.

## Broker priority

Use the strongest available transport:

1. **Agent Teams** when enabled and stable in the local Claude Code install.
2. **Background subagents + hooks** when Agent Teams are unavailable.
3. **Explicit copy-back** when automation is unavailable: role session returns
   `RoleReturnSignal` and the orchestrator records it manually.

All three transports must write the same state shape.

## Procedure

1. Initialize or read V2 host state:

   ```bash
   arcgentic v2-session-plan \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker
   ```

2. For each created/resumed Claude Code role context, record its broker id:

   ```bash
   arcgentic v2-record-session \
     --state .agentic-rounds/state.yaml \
     --host claude-code-broker \
     --role <planner|developer|auditor> \
     --thread-id <broker-session-id>
   ```

3. Inject only that role's prompt. The developer does not receive auditor
   reasoning. The auditor does not receive developer chat transcript. The
   planner owns phase decisions.

4. Require every role turn to end with `RoleReturnSignal` JSON.

5. Record the signal:

   ```bash
   arcgentic v2-return-signal \
     --state .agentic-rounds/state.yaml \
     --signal-json '<RoleReturnSignal JSON>'
   ```

6. Re-run `v2-session-plan --host claude-code-broker` and dispatch the next
   role.

## Hook guidance

When hooks are available, configure stop hooks to extract the role's final
response and pass it back to the orchestrator as context. The hook must not
invent a PASS/NEEDS_FIX outcome. It only transports the role's own
`RoleReturnSignal`.

## Fail-closed rules

- If a role returns prose without valid `RoleReturnSignal`, do not advance.
- If the broker cannot identify which role produced a signal, do not advance.
- If a role tries to rename itself outside the four fixed titles, reject it.
- If Claude Code transport is unavailable, fall back to explicit copy-back
  rather than pretending automation succeeded.
