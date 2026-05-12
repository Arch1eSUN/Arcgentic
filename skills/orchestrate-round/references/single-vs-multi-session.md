# Single-session vs multi-session mode

## Two operating modes

arcgentic supports two ways to run the four-role workflow:

### Mode A — Single-session (orchestrator drives all)

ONE Claude session. Loaded skill: `arcgentic:orchestrate-round`. Acts as orchestrator. Dispatches role sub-agents via Task tool when role-switching is needed.

**Pros**:
- Faster iteration (no human in the loop between roles)
- Easier to debug (one transcript)
- Lower coordination cost

**Cons**:
- Sub-agent context isolation is the only thing preventing context contamination — if dispatch is misused, audit independence breaks
- State changes are all in one place (good for traceability, bad for distributed teams)

**Use when**:
- Independent developer working solo
- Small project (< 5 rounds total)
- Trial mode (proving out the workflow)
- No human team to distribute roles to

### Mode B — Multi-session (humans coordinate)

MULTIPLE Claude sessions, each loaded with a different role skill:
- Session 1 (founder + planner): loads `arcgentic:plan-round`
- Session 2 (developer): loads `arcgentic:execute-round`
- Session 3 (auditor): loads `arcgentic:audit-round`
- Session 4 (ref-tracker, optional): loads `arcgentic:track-refs`

State.yaml is the inter-session protocol. Every session reads it on entry.

**Pros**:
- True audit independence (auditor never sees dev/planner reasoning, even via sub-agent dispatch)
- Distributed work (different humans run different sessions)
- Multi-day workflows (sessions don't need to be contemporaneous)

**Cons**:
- Higher coordination cost (state.yaml + handoff docs must be the comms protocol)
- Slower iteration (humans must trigger session changes)
- More chances for state.yaml drift if sessions get out of sync

**Use when**:
- Team has multiple humans
- Project is long-lived (months of rounds)
- Audit independence is critical (e.g. compliance-sensitive software)
- Different humans have different role expertise

## Switching modes mid-round

Possible but risky. The state.yaml itself doesn't care which mode you're in. To switch:
1. Whatever mode you're in, finish the current state
2. Switch — load the new mode's skill on the new session
3. Re-read state.yaml; let pickup.sh tell you where you are

The risk: if you switch from single-session to multi-session and the auditor session reads sub-agent transcripts from the previous orchestrator session, audit independence is broken. Mitigation: clear conversation history between switches.

## Decision flowchart

```
Are you working with a team of humans?
├── YES → Mode B (multi-session)
└── NO → Are audit independence requirements strict (compliance, regulated)?
        ├── YES → Mode B (multi-session) anyway
        └── NO → Mode A (single-session)
```

## State.yaml visibility

In Mode A, `.agentic-rounds/state.yaml` lives in the project repo (gitignored by default). The orchestrator session updates it.

In Mode B, all human sessions need access to `.agentic-rounds/state.yaml`. Two options:
1. **Local**: each human's session runs on a machine with the project repo cloned; they pull/push state.yaml manually (or via a shared Git remote)
2. **Shared**: state.yaml lives in a shared store (Google Drive / iCloud / Dropbox) symlinked into each project root

Option 1 is simpler; Option 2 is more real-time. Either works.
