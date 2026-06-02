# R1-v1-openspec-marketplace — V1 Source Intake + Spec Governance Handoff

**Phase**: arcgentic v1.0.0
**Round**: R1-v1-openspec-marketplace
**Type**: substrate-touching round
**Prior-round anchor**: `bff83e2a9c56bbd7421492ead646e9aa087b12c5`
**Design contract**: `docs/plans/2026-06-02-arcgentic-v1-openspec-superpowers-design.md`
**Audit script**: `arcgentic audit-check docs/audits/R1-v1-openspec-marketplace.md --strict-extended`
**Cost discipline**: no paid API calls, no background polling, no automatic third-party plugin install

---

## 1. Scope

Allowed scope: implement the first V1 slice that makes external workflow sources first-class
arcgentic inputs. The slice adds source-intake, capability-registry, spec-governance, and
v1-release-readiness seams with tests and CLI exposure.

Forbidden scope: do not depend on the OpenSpec npm package, do not vendor Superpowers
Marketplace plugins, do not auto-install third-party plugins, do not add hosted services,
and do not touch Moirai.

This round converts the V1 design document into implementation-ready tasks. It must keep
arcgentic's round state machine as the enforcement layer and treat OpenSpec/Superpowers
as source models.

## 2. Reference Scan

| Reference | Use mode | Why used | What part | License + RT tier |
|---|---|---|---|---|
| `obra/superpowers-marketplace` | reference-only | Provides marketplace catalog shape for skills and workflows | `.claude-plugin/marketplace.json` entries: name, source, version, strict, description | public GitHub source; RT0 |
| `wearetechnative/awesome-openspec` | reference-only | Provides spec-driven artifact lifecycle examples | `proposal.md`, `design.md`, `tasks.md`, `openspec/specs`, archive model | public GitHub source; RT0 |
| `docs/plans/2026-06-02-arcgentic-v1-openspec-superpowers-design.md` | direct use | Local design contract already committed and pushed | V1 scope, module seams, tests, release gates | project-owned; RT3 |

Reference use rule: these sources inform arcgentic-native modules. No third-party code is
copied into runtime.

## 3. Tooling Plan

Expected skills: `arcgentic:using-arcgentic`, `arcgentic:plan-round`,
`arcgentic:execute-round`, `arcgentic:audit-round`, and `arcgentic:codify-lesson`.

Expected CLI commands: `arcgentic validate-handoff`, `arcgentic quality-gate-enforce`,
`arcgentic audit-check`, `pytest`, `mypy --strict`, `ruff check`, and plugin validator.

Known adapter finding: `plan-round-impl` dispatch failed in this Codex Desktop context
because the current adapter detection chose a host path that cannot dispatch `planner`.
Developer must keep this as a V1 readiness finding and avoid relying on fake sub-agent
success.

## 4. Architecture Target

Add three deep modules behind small interfaces:

- `source-intake`: normalize repo/catalog/spec sources into auditable source records.
- `capability-registry`: parse marketplace-style catalogs into normalized capabilities.
- `spec-governance`: validate OpenSpec-style artifact graphs without requiring OpenSpec CLI.

Add one release gate module:

- `v1-release-readiness`: verify version surfaces, plugin manifests, local install shape,
  and release/dogfood artifacts.

## 5. Implementation Tasks

Implementation task 1: add fixtures for Superpowers-style and Codex-style marketplace
catalogs plus OpenSpec-style change directories.

Implementation task 2: implement source-intake data model, schema validation, and CLI
entry point.

Implementation task 3: implement capability-registry parser and duplicate detection.

Implementation task 4: implement spec-governance artifact graph validator, task status
counter, and archive readiness checks.

Implementation task 5: implement v1-release-readiness gate and wire it into CLI.

Implementation task 6: update relevant skills and README surfaces without changing runtime
scope.

## 6. Required Tests

Required test: source-intake accepts repo, marketplace, and openspec source records and
rejects malformed or duplicate records.

Required test: capability-registry parses Superpowers-style `.claude-plugin/marketplace.json`
and Codex-style `.agents/plugins/marketplace.json`.

Required test: spec-governance detects missing proposal/design/tasks, incomplete tasks,
and archive target collisions.

Required test: v1-release-readiness fails on version drift across `plugin.json`,
`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `toolkit/pyproject.toml`,
`README.md`, and `README.zh-CN.md`.

Required test: existing `277` toolkit tests remain green after implementation.

## 7. Required Audit Facts

Required audit fact 1: `git rev-parse HEAD` equals the final dev-body anchor recorded in
self-audit.

Required audit fact 2: `python3 -m pip show arcgentic` reports editable project location
under this repository's `toolkit`.

Required audit fact 3: plugin validator passes for `/Users/archiesun/plugins/arcgentic`.

Required audit fact 4: source-intake tests cover both external source URLs from this round.

Required audit fact 5: capability-registry tests prove both marketplace formats.

Required audit fact 6: spec-governance tests prove proposal/design/tasks archive semantics.

Required audit fact 7: anti-scope grep proves no OpenSpec npm dependency was added.

Required audit fact 8: anti-scope grep proves no Moirai path was modified.

## 8. Stop Conditions

Stop condition: if adapter dispatch still fails after a minimal reproduction, do not fake
sub-agent success; write an adapter bug finding and continue only through verified local
scripts.

Stop condition: if any implementation requires a paid API, background process, or automatic
third-party plugin install, stop and rescope.

Stop condition: if version/readme/plugin surfaces drift during V1 release work, stop and
repair before tagging.

## 9. BA Design Brief

BA designer should decide whether source records are YAML or JSON, whether archive readiness
should move files or validate only, and whether capability tags are inferred from descriptions
or only explicit metadata.

The architectural target is to keep source intake and spec governance as inputs to planning,
not as replacement states for the round state machine.

## 10. CR Review Brief

CR reviewer should prioritize shallow pass-through modules, parser fragility, hidden external
dependencies, and release-surface drift. Any module whose interface mirrors only one caller
must be challenged unless it hides real parsing or validation complexity.

## 11. SE Contract Brief

SE reviewer receives only this handoff sections 1-8 and the public interface contracts. SE
must not receive BA design rationale. Threat surfaces: path traversal in source paths, remote
URL trust, malformed marketplace JSON, archive path collision, and accidental secret output
from config inspection.

## 12. Commit Plan

Commit 1: this handoff and state update.

Commit 2: source-intake fixtures, model, validator, and tests.

Commit 3: capability-registry + spec-governance modules, CLI, and tests.

Commit 4: v1-release-readiness gate, skill/readme updates, and self-audit handoff.

## 13. Quality Gates

Every code commit must run:

- `cd toolkit && pytest --tb=short -q`
- `cd toolkit && mypy --strict src/ tests/`
- `cd toolkit && ruff check .`
- `python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic`

## 14. State Handling

State file: `.agentic-rounds/state.yaml`.

Current round id: `R1-v1-openspec-marketplace`.

Expected state path: `planning -> awaiting_dev_start -> dev_in_progress -> awaiting_audit
-> audit_in_progress -> passed -> closed`.

## 15. Devsession Message

Read: `docs/superpowers/plans/2026-06-02-R1-v1-openspec-marketplace-handoff.md` and
`docs/plans/2026-06-02-arcgentic-v1-openspec-superpowers-design.md`.

Start round: `R1-v1-openspec-marketplace`.

Stop after: Commit 4 self-audit handoff is written, local gates are green, and external
audit is ready to run.

## 16. Forward Debt

Forward debt P2: adapter detection currently treats a local `~/.claude/skills` directory as
Claude Code availability. V1 should tighten dispatch readiness checks so installed files do
not imply a working agent dispatch transport.

Forward debt P3: `start-round` is not yet a deep CLI seam; this run manually set round id
and transitioned to planning.

## 17. Next Round Preview

After V1 implementation passes audit, the next round should be release hardening:
version-surface alignment, README cleanup, package build, tag, push, and portability proof.

## 18. Acknowledgments

This handoff was written during arcgentic-on-arcgentic dogfood in Codex Desktop on
2026-06-02.

*Substrate-touching round handoff written by planner role using verified local arcgentic scripts.*
