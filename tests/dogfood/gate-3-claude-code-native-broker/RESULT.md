# Dogfood Gate 3 — Claude Code V2 Native-Tooling Broker (tier 0)

**Date:** 2026-08-12
**Mode tested:** single-session-subagent (foreground `Agent` dispatch only — `multi-session-subthread`/background dispatch was NOT tested in this gate; do not claim it was)
**Scratch project:** /tmp/arcgentic-dogfood-gate3/toy-project (outside the arcgentic repo; not committed)

## What was tested

Followed `skills/claude-code-session-broker/SKILL.md`'s tier-0 procedure by hand,
end to end, for one Planner dispatch, using the controller session's own
`Agent`/`SendMessage`/`ListAgents` tools directly (not simulated, not described —
actually executed).

## Commands run and real output

### Setup

```
$ mkdir -p /tmp/arcgentic-dogfood-gate3/toy-project && cd /tmp/arcgentic-dogfood-gate3/toy-project
$ git init -q
$ echo "# Toy project for arcgentic Claude Code V2 dogfood gate 3" > README.md
$ git add README.md && git commit -q -m "init toy project"
$ git log --oneline
bdf01f6 init toy project
```

`.agentic-rounds/state.yaml` bootstrapped with `arcgentic_v2.host: claude-code-broker`,
`mode: single-session-subagent`, `current_round: {id: R1, state: intake}`.

### Step 1 — `v2-session-plan`

```
$ arcgentic v2-session-plan \
  --state .agentic-rounds/state.yaml \
  --host claude-code-broker \
  --user-request 'Add a one-line CONTRIBUTING.md note saying pull requests are welcome.'
```

Returned a JSON dispatch plan with `orchestrator_status: "active"`, `next_role: "planner"`,
and `actions[0]` = `{kind: "create", role: "planner", target: "subagent",
thread_id: "subagent:planner", title: "Planner", prompt: "<full role_prompt() text>"}`.
The `prompt` field was the complete, unmodified Planner role prompt (fixed-role
boundaries, footer format instructions, routing rules) exactly as
`v2_session_orchestration.role_prompt()` generates it — not edited before dispatch.

### Step 2 — dispatch via `Agent` (foreground, tier-0 step 4)

Called the `Agent` tool with `prompt` = `actions[0].prompt` verbatim, `run_in_background: false`,
`subagent_type: "general-purpose"`, working directory set to the toy project.

**Returned `agentId`: `a96c67bffafa0c5b4`**

The agent's full response (its role-owned work, done in the same call — no separate
turn needed to "acknowledge" the role first):

- Read `.agentic-rounds/state.yaml`, confirmed round R1 / state `intake` / the user request.
- Did a real reference/tool discovery pass (used `WebSearch`) — cited PyTorch/Facebook-OSS
  "we actively welcome your pull requests" phrasing and GitHub's own docs on `CONTRIBUTING.md`
  placement.
- Considered and explicitly rejected heavier tooling (documentation-authoring agents,
  the source-intake skill) as over-engineering for a one-sentence file.
- Wrote a real handoff document to `docs/plans/R1.md` (confirmed on disk: 79 lines,
  6066 bytes — verified with `ls -la` / `wc -l` after the call returned, not just claimed
  by the agent).
- Returned exactly one well-formed ` ```arcgentic-role-return ... ``` ` fenced JSON footer
  on the first attempt — **no `SendMessage` correction was needed** (tier-0 step 8's
  correction loop was not exercised in this run, since the footer was valid immediately).

### Steps 5-6 — `v2-record-session` / `v2-dispatch-role`

```
$ arcgentic v2-record-session --state .agentic-rounds/state.yaml --host claude-code-broker \
  --role planner --thread-id a96c67bffafa0c5b4
{"recorded": true, "role": "planner", "thread_id": "a96c67bffafa0c5b4"}

$ arcgentic v2-dispatch-role --state .agentic-rounds/state.yaml --host claude-code-broker \
  --role planner --thread-id a96c67bffafa0c5b4
{
  "dispatched": true,
  "orchestrator_status": "sleeping",
  "pending_role": "planner",
  "thread_id": "a96c67bffafa0c5b4"
}
```

`state.yaml` after this step: `orchestrator_status: sleeping`, `pending_role: planner`,
`pending_thread_id: a96c67bffafa0c5b4`, `role_sessions.planner` recorded with a real
`updated_at` timestamp.

### Step 7-8 — collect output, validate footer

Since this was a foreground `Agent` call, its return value (captured above in Step 2) IS
the role's output — no waiting, no task-notification needed. The response was inspected
directly for the required ` ```arcgentic-role-return ``` ` fence: present, exactly once,
valid JSON, all required fields (`role`, `status`, `round_id`, `state`, `artifacts`,
`next_recommended_role`) present, no extra fields.

### Step 9 — `v2-return-signal`

```
$ arcgentic v2-return-signal --state .agentic-rounds/state.yaml --signal-json '<the footer JSON from Step 2, verbatim>'
{
  "next_role": "developer",
  "recorded": true
}
```

`state.yaml` after this step (full contents captured): `current_round.state` advanced
`intake` → `awaiting_dev_start`; `state_history` gained one entry (`state: awaiting_dev_start,
by: planner`, real ISO timestamp, `artifact` = the JSON project_plan payload);
`orchestrator_status` returned to `active`; `pending_role`/`pending_thread_id`/`pending_since`
cleared; `next_role: developer`; `last_signal` recorded the full planner signal.

## Outcome

- [x] `v2-session-plan` returned a valid dispatch plan with `actions[0].prompt`
- [x] Foreground `Agent` call returned a response containing a valid `arcgentic-role-return`
      footer on the first attempt (no `SendMessage` correction was needed)
- [x] `v2-record-session` succeeded
- [x] `v2-dispatch-role` succeeded
- [x] `v2-return-signal` accepted the footer JSON and advanced `current_round.state` correctly
      (`intake` → `awaiting_dev_start`, `orchestrator_status` `active` → `sleeping` → `active`,
      `next_role` correctly set to `developer`)

## Verdict

**PASS** — the tier-0 procedure in `skills/claude-code-session-broker/SKILL.md` was followed
literally, step by step, using real `Agent` tool calls against a real (if toy) project, and
every step produced the expected result with no manual intervention or correction. This gate
covers `single-session-subagent` mode via a foreground `Agent` dispatch only. NOT covered by
this gate: `multi-session-subthread` mode (background `Agent` + task-notification collection),
the `SendMessage`-based footer-correction path (step 8's retry loop never triggered since the
footer was valid on the first attempt), and the hook-fallback procedure (untouched — its own
existing test suite in `toolkit/tests/unit/test_claude_code_broker.py` covers that path
separately and was not re-verified here).
