---
name: agency-roster
description: Use when a round references agency-agents catalogs, role-family routing, multi-agent identity prompts, or English/Chinese specialist role catalogs.
---

# agency-roster

Parses agency-agents-style catalogs as role-family references for arcgentic identity
handoffs.

## Workflow

1. Inspect the catalog locally:

   ```bash
   arcgentic agency-roster inspect <catalog-path>
   ```

2. Select role families for the round, such as minimal-change engineer, software architect,
   security engineer, code reviewer, or auditor.
3. Use selected role families to improve identity handoff prompts.

## Boundaries

- Role catalogs are references, not imported arcgentic agents.
- Do not vendor upstream role files.
- Do not replace planner/developer/auditor state identities with agency roles.
