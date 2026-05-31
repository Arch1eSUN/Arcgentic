---
name: track-refs
description: Maintain references/INDEX.md, classify reference RT tier, and emit BA-design triplet rows. Use when adding or refreshing reference projects.
---

# track-refs

Maintains the local reference catalog used by planning and BA design passes.

## When to invoke

- BA design pass needs a reference scan table
- User adds a local reference repo under `references/`
- A round needs reference relevance refreshed

## Commands

Add a local reference:

```bash
arcgentic track-refs add references/<repo> \
  --owner-repo owner/repo \
  --round R1 \
  --usage-evidence '{"pattern_only": true}'
```

Emit BA-design triplet row:

```bash
arcgentic track-refs triplet references/<repo> \
  --owner-repo owner/repo \
  --round R1 \
  --usage-evidence '{"pattern_only": true}'
```

Refresh relevance marker:

```bash
arcgentic track-refs refresh-relevance --round R1
```

## RT tiers

| Tier | Meaning |
|---|---|
| RT0 | Pattern-only reference; no copied/runtime dependency |
| RT1 | Source-adapted code allowed by license |
| RT2 | Binary vendored/distributed |
| RT3 | Imported at runtime |

GPL/AGPL source adaptation is forced to RT0 unless separately approved.

## See also

- `agents/ref-tracker.md`
- `toolkit/src/arcgentic/skills_impl/track_refs.py`

