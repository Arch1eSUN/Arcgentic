# arcgentic v0.3 integration plan — OpenSpec + Superpowers Marketplace

**Status:** deferred roadmap, not part of v0.2.2.

## 1. Boundary

v0.2.2 finishes the original P0/P1/P2 plan. v0.3 is the first version allowed to
integrate external workflow systems:

- `wearetechnative/awesome-openspec` / OpenSpec ecosystem
- `obra/superpowers-marketplace`

## 2. Layering decision

| Layer | Owner | Purpose |
|---|---|---|
| Spec source | OpenSpec | Proposal, delta specs, design, tasks, archive |
| Capability source | Superpowers Marketplace | Discover optional plugins/skills/workflows |
| Orchestration | arcgentic | Round plan, reference use, tooling scan, dev handoff, audit verdict |

arcgentic must not replace OpenSpec's spec format, and OpenSpec must not replace
arcgentic's PASS/NEEDS_FIX external audit loop.

## 3. v0.3 candidate work

1. Add `openspec ingest` support:
   - read `openspec/specs/**/spec.md`
   - read `openspec/changes/<id>/proposal.md`
   - read `openspec/changes/<id>/design.md`
   - read `openspec/changes/<id>/tasks.md`
   - emit a `Spec source` section for plan-round handoff

2. Add marketplace capability scan:
   - read `.claude-plugin/marketplace.json`
   - map plugin metadata to candidate capabilities
   - mark each capability as `available`, `relevant-not-installed`, or `rejected`

3. Connect both to source-rule handoff validation:
   - require spec-source evidence when OpenSpec is present
   - require capability scan evidence when marketplace metadata is present
   - preserve current optional behavior when neither exists

4. Extend `track-refs`:
   - GitHub search/discovery
   - provenance and license capture
   - explicit use-mode mapping to source-rule table

## 4. Non-goals

- Do not auto-install marketplace plugins.
- Do not invoke paid APIs.
- Do not make OpenSpec mandatory for projects that already have another spec source.
- Do not let marketplace capability discovery override round scope.
