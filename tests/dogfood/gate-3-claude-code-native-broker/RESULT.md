# Dogfood Gate 3 — Claude Code V2 Native-Tooling Broker (tier 0)

**Date:** 2026-08-12
**Mode tested:** single-session-subagent (foreground `Agent` dispatch only — `multi-session-subthread`/background dispatch was NOT tested in this gate; do not claim it was)
**Scratch project:** /tmp/arcgentic-dogfood-gate3/toy-project (outside the arcgentic repo; not committed)

## What was tested

Followed `skills/claude-code-session-broker/SKILL.md`'s tier-0 procedure by hand,
end to end, for one Planner dispatch, using the controller session's own `Agent`
tool directly (not simulated, not described — actually executed). The footer
was valid on the first attempt, so `SendMessage` (the step-8 correction path)
was never invoked, and this was a foreground call, so `ListAgents` was never
needed either — both are exercised by neither this run nor this document; see
the Verdict section for the full list of what remains untested.

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

Real, verbatim output (the `prompt` field is `v2_session_orchestration.role_prompt()`'s
complete, unedited text — this is exactly what got passed to `Agent` in Step 2 below,
character for character):

```json
{
  "actions": [
    {
      "kind": "create",
      "prompt": "You are Planner.\nCurrent round: R1\nCurrent state: intake\nCurrent user request: Add a one-line CONTRIBUTING.md note saying pull requests are welcome.\nRead .agentic-rounds/state.yaml before acting.\nUse Arcgentic V2 fixed-role boundaries:\n- Planner owns brainstorming, the full project plan, phase/round decomposition, and per-round gate decisions.\n- Developer owns implementation, self-audit, and NEEDS_FIX repair.\n- Test owns strict reality QA / simulated user-session testing only when the current round's project_plan.test_gate requires it.\n- Auditor owns stricter independent PASS / NEEDS_FIX / AUDIT_INCOMPLETE review and must not trust Developer self-audit as proof.\n- Orchestrator owns routing, state recording, and phase/project close only.\nOnly the Orchestrator may mutate .agentic-rounds/state.yaml, dispatch roles, or record role return signals. Planner, Developer, Test, and Auditor must write their own artifacts only, then return JSON for Orchestrator to consume.\nDo not stop after acknowledging the role. Complete the role-owned work in this turn, using tools as needed, before returning the RoleReturnSignal.\nDeveloper, Test, and Auditor must use project.arcgentic_v2.last_signal.artifacts to locate the prior role artifact they need to consume.\nPlanner must produce a complete project plan before the first Developer round. The plan must split the project into phases and rounds, and each round must declare gates including whether Test is required. Put a structured project_plan object in artifacts.project_plan, not only prose.\nPlanner must first do a reference/tool discovery pass for the user's idea: search GitHub or equivalent public sources for reliable comparable projects or effective implementation references, scan locally available skills, plugins, MCP servers, connectors, and CLI tools, and write the selected references/tools into the detailed Markdown handoff. Every round handoff must include which references to inspect, which skills/MCP/plugins/tools to use, which ones were considered but rejected, and why.\nPlanner handoffs are full Markdown engineering documents, not short JSON summaries. The Orchestrator may transfer prompt instructions between threads, but each role session must read the referenced handoff artifact before doing role-owned work.\nDeveloper must create a local git commit after implementation and verification. Use git add for the files owned by the round, create a normal local commit, verify it with `git rev-parse HEAD`, then include that hash in the return footer. Developer always returns self_audit and commit. If the current round's project_plan.test_gate.required is true, route to awaiting_test/test. If it is false, route directly to awaiting_audit/auditor and include the skip reason in the human-readable summary. A GitHub remote is stronger evidence but is not required for local audit.\nTest is optional and must run only when the project_plan for this round requires it. When required, Test must simulate realistic user behavior with domain-specific strictness: UI spacing/radius/alignment/states, scroll and frame-rate observations, responsive behavior, CLI install/help/stdin/stderr/exit codes, or agent end-to-end user conversations as appropriate. Test writes a readable user-test artifact and returns awaiting_audit only when the simulated user flow passes. If the user flow fails, route to needs_fix/developer.\nAuditor is stricter than Developer self-audit. Auditor must independently replay evidence, verify commit anchors and required/skipped Test gates, check scope against the plan, and reject PASS when the evidence chain is insufficient. Auditor verdicts must include a fact-table section headed exactly `## 7. Fact table` or `## § 7. Mechanical audit facts`, use the exact markdown table header `| # | Command | Expected | Comment |`, keep expected values exact, do not add a separate Actual column, and run `arcgentic audit-check <verdict> --strict --strict-extended` before returning PASS. Auditor PASS fact rows must use stable evidence such as committed artifacts, fixed git hashes, artifact file contents, and test/build outputs. Do not use mutable live routing state such as `current_round.state`, `project.arcgentic_v2.last_signal.role`, or `project.arcgentic_v2.last_signal.state` as PASS facts unless the command reads an immutable committed snapshot. Auditor PASS returns must also include artifacts.commit as the 40-hex local audit commit anchor for the committed verdict.\nUse natural language for your role-owned output: Planner writes a readable plan, Developer writes a readable self-audit summary, Test writes a readable user-test report, and Auditor writes a readable verdict. Do not make the whole response raw JSON.\nRecommended closing shape: first write 3-8 concise human-readable bullets covering what you decided or completed, where the artifact lives, and what the next role should do. Then add the fenced routing footer below.\nAt the end of your role-owned output, include exactly one machine-readable footer. Format the JSON over multiple lines with indentation so humans can read it:\n```arcgentic-role-return\n{\n  \"role\": \"planner\",\n  \"status\": \"planned\",\n  \"round_id\": \"R1\",\n  \"state\": \"awaiting_dev_start\",\n  \"artifacts\": {\n    \"handoff\": \"docs/plans/R1.md\",\n    \"project_plan\": {\n      \"phases\": [\n        {\n          \"id\": \"P1\",\n          \"rounds\": [\n            {\n              \"id\": \"R1\",\n              \"handoff\": \"docs/plans/R1.md\",\n              \"test_gate\": {\n                \"required\": false,\n                \"reason\": \"No separate reality QA gate is needed for this round.\"\n              }\n            }\n          ]\n        }\n      ]\n    }\n  },\n  \"next_recommended_role\": \"developer\"\n}\n```\nOrchestrator thread id is not recorded in state. Report this as a blocking orchestration setup issue instead of assuming the Orchestrator can poll your thread.\nDo not add extra fields outside role, status, round_id, state, artifacts, and next_recommended_role.\nPlanner may route only to awaiting_dev_start/developer, planning/planner, or closed/null for final project completion. For closed returns, Planner must write the closeout artifact, create a local closeout commit, verify `git rev-parse HEAD`, and include artifacts.closeout plus artifacts.commit in the return footer.\nIf the current state is closed and the user request asks for new work, Planner must decide the next phase or next round instead of returning closed.\nDeveloper may route only to awaiting_test/test, awaiting_audit/auditor, or needs_fix/developer.\nTest may route only to awaiting_audit/auditor or needs_fix/developer.\nAuditor may route only to passed/planner, needs_fix/developer, or audit_in_progress/auditor. Auditor may use audit_in_progress/auditor only for retryable audit work. If the same evidence gap cannot be resolved by another audit pass, route to needs_fix/developer or stop with a concise AUDIT_INCOMPLETE report instead of creating an audit loop.",
      "role": "planner",
      "target": "subagent",
      "thread_id": "subagent:planner",
      "title": "Planner"
    }
  ],
  "current_round": "R1",
  "current_state": "intake",
  "host": "claude-code-broker",
  "mode": "single-session-subagent",
  "next_role": "planner",
  "orchestrator_status": "active",
  "pending_role": null,
  "pending_thread_id": ""
}
```

### Step 2 — dispatch via `Agent` (foreground, tier-0 step 4)

Called the `Agent` tool with `prompt` = `actions[0].prompt` verbatim (the full text shown
above), `run_in_background: false`, `subagent_type: "general-purpose"`. The `Agent` tool
has no separate working-directory parameter — the controller's own shell had already `cd`'d
into `/tmp/arcgentic-dogfood-gate3/toy-project` before this call, and the dispatched agent
inherited that cwd, which is why its relative-path file operations (`.agentic-rounds/state.yaml`,
`docs/plans/R1.md`) landed in the toy project rather than the arcgentic repo.

**Returned `agentId`: `a96c67bffafa0c5b4`**

Full raw response text, verbatim (this is the entire return value — nothing trimmed;
outer fence uses 4 backticks since the response itself contains a 3-backtick fence):

````
Reference/tool discovery pass complete, and the R1 handoff document is written.

- Read `.agentic-rounds/state.yaml`: round R1, state `intake`, request is "Add a one-line CONTRIBUTING.md note saying pull requests are welcome."
- Did a public reference scan (WebSearch): selected the PyTorch-examples / Facebook-OSS "we actively welcome your pull requests" phrasing as the wording register, and GitHub's own docs confirming `CONTRIBUTING.md` at repo root as the correct location.
- Scanned local skills/plugins/MCP/CLI: none needed — plain `Write`/`Edit` is the right tool for a one-sentence file; documentation-authoring agents and the source-intake skill were considered and rejected as over-engineering for this scope.
- Decided this is a single-round project (P1/R1 only): the entire ask is one new file, one sentence.
- Set `test_gate.required = false` for R1 with an explicit reason (static doc file, no runtime/UI/CLI surface — Auditor's mechanical file/commit check is sufficient evidence).
- Full handoff doc written to `docs/plans/R1.md` (repo-relative), covering scope, out-of-scope, reference table, tool-discovery table, acceptance criteria, and next-role instructions for Developer.
- Note: I have no visibility into the Orchestrator's own thread id — routing back to it depends on the harness, not on anything I can record in state.

```arcgentic-role-return
{
  "role": "planner",
  "status": "planned",
  "round_id": "R1",
  "state": "awaiting_dev_start",
  "artifacts": {
    "handoff": "docs/plans/R1.md",
    "project_plan": {
      "phases": [
        {
          "id": "P1",
          "rounds": [
            {
              "id": "R1",
              "handoff": "docs/plans/R1.md",
              "test_gate": {
                "required": false,
                "reason": "Static one-line CONTRIBUTING.md documentation file; no executable behavior, UI, or CLI surface to simulate. Auditor's mechanical file/commit checks are sufficient evidence."
              }
            }
          ]
        }
      ]
    }
  },
  "next_recommended_role": "developer"
}
```
````

Independently confirmed on disk after the call returned (not just claimed by the agent):
`ls -la docs/plans/` showed `R1.md`, `wc -l docs/plans/R1.md` → 79 lines / 6066 bytes.

Returned exactly one well-formed ` ```arcgentic-role-return ... ``` ` fenced JSON footer
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

The exact command run (the footer JSON from Step 2, pasted verbatim as the `--signal-json`
value — this is the real command, not a placeholder):

```
$ arcgentic v2-return-signal \
  --state .agentic-rounds/state.yaml \
  --signal-json '{
  "role": "planner",
  "status": "planned",
  "round_id": "R1",
  "state": "awaiting_dev_start",
  "artifacts": {
    "handoff": "docs/plans/R1.md",
    "project_plan": {
      "phases": [
        {
          "id": "P1",
          "rounds": [
            {
              "id": "R1",
              "handoff": "docs/plans/R1.md",
              "test_gate": {
                "required": false,
                "reason": "Static one-line CONTRIBUTING.md documentation file; no executable behavior, UI, or CLI surface to simulate. Auditor'"'"'s mechanical file/commit checks are sufficient evidence."
              }
            }
          ]
        }
      ]
    }
  },
  "next_recommended_role": "developer"
}'
{
  "next_role": "developer",
  "recorded": true
}
```

Full `state.yaml` contents after this step, verbatim (`cat .agentic-rounds/state.yaml`):

```yaml
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
    role_sessions:
      planner:
        role: planner
        title: Planner
        thread_id: a96c67bffafa0c5b4
        host: claude-code-broker
        updated_at: '2026-08-12T13:18:18Z'
    active_user_request: Add a one-line CONTRIBUTING.md note saying pull requests
      are welcome.
    orchestrator_status: active
    project_plan:
      phases:
      - id: P1
        rounds:
        - id: R1
          handoff: docs/plans/R1.md
          test_gate:
            required: false
            reason: Static one-line CONTRIBUTING.md documentation file; no executable
              behavior, UI, or CLI surface to simulate. Auditor's mechanical file/commit
              checks are sufficient evidence.
    last_signal:
      role: planner
      status: planned
      round_id: R1
      state: awaiting_dev_start
      artifacts:
        handoff: docs/plans/R1.md
        project_plan:
          phases:
          - id: P1
            rounds:
            - id: R1
              handoff: docs/plans/R1.md
              test_gate:
                required: false
                reason: Static one-line CONTRIBUTING.md documentation file; no executable
                  behavior, UI, or CLI surface to simulate. Auditor's mechanical file/commit
                  checks are sufficient evidence.
      next_recommended_role: developer
    next_role: developer
current_round:
  id: R1
  state: awaiting_dev_start
  state_history:
  - state: awaiting_dev_start
    ts: '2026-08-12T13:18:31Z'
    by: planner
    artifact: '{"handoff": "docs/plans/R1.md", "project_plan": {"phases": [{"id":
      "P1", "rounds": [{"handoff": "docs/plans/R1.md", "id": "R1", "test_gate": {"reason":
      "Static one-line CONTRIBUTING.md documentation file; no executable behavior,
      UI, or CLI surface to simulate. Auditor''s mechanical file/commit checks are
      sufficient evidence.", "required": false}}]}]}}'
states: {}
```

Confirms: `current_round.state` advanced `intake` → `awaiting_dev_start`; `orchestrator_status`
returned to `active`; `pending_role`/`pending_thread_id`/`pending_since` cleared; `next_role:
developer`; `last_signal` recorded the full planner signal.

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
