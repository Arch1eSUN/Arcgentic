---
name: cross-session-handoff
description: Read, write, snapshot, and lock .arcgentic/state.yaml across planner, dev, audit, and optional test sessions.
---

# cross-session-handoff

Manages `.arcgentic/state.yaml` as the shared state medium across multiple AI
sessions.

## Commands

```bash
arcgentic cross-session-handoff read
arcgentic cross-session-handoff write --session-id dev-session --updates '{"current_phase":"dev"}'
arcgentic cross-session-handoff snapshot --session-id audit-session
arcgentic cross-session-handoff acquire-lock --session-id dev-session --ttl 600
arcgentic cross-session-handoff release-lock --session-id dev-session
```

## Rules

- Reads do not acquire a lock.
- Writes acquire a TTL lock, write through a temp file, then rename atomically.
- Snapshots go to `.arcgentic/state-history/`.
- A session must not overwrite another non-expired lock.

## See also

- `toolkit/src/arcgentic/skills_impl/cross_session_handoff.py`

