# arcgentic v1.0.0 — OpenSpec + Superpowers Marketplace Design

## 1. Problem framing

arcgentic v0.2.2-alpha.3 already provides the round state machine, role skills, audit
fact checks, lesson codification, reference tracking, cross-session handoff, and Python
CLI gates. The v1.0.0 upgrade should make the upstream planning and capability context
more explicit without weakening the existing enforcement model.

Two external workflow sources are being fused:

- `obra/superpowers-marketplace`: a Claude Code marketplace catalog for skills,
  workflows, and productivity plugins.
- `wearetechnative/awesome-openspec`: an OpenSpec / Spec-Driven Development resource
  catalog that also dogfoods OpenSpec-style `proposal.md`, `design.md`, `tasks.md`,
  `specs/`, and `archive/` artifacts.

The v1 goal is not to wrap either project directly. The goal is to absorb their useful
workflow patterns into arcgentic's own mechanically-verifiable round model.

## 2. Source facts

### 2.1 Superpowers Marketplace facts

- The marketplace has a `.claude-plugin/marketplace.json` catalog with plugin entries.
- Each entry includes a plugin `name`, source URL or local source descriptor, `version`,
  `description`, and `strict` flag.
- The current catalog includes workflow/capability plugins such as `superpowers`,
  `superpowers-chrome`, `episodic-memory`, `superpowers-lab`,
  `superpowers-developing-for-claude-code`, `claude-session-driver`, and
  `double-shot-latte`.
- The useful arcgentic pattern is capability discovery from a signed/known catalog, not
  copying third-party skills into arcgentic.

### 2.2 Awesome OpenSpec facts

- OpenSpec is described as a spec-driven development workflow where user and assistant
  agree on what to build before code is written.
- The core lifecycle is proposal/spec/design/tasks before implementation, then archive
  after completion.
- The sample change `github-stats-script` contains `.openspec.yaml`, `proposal.md`,
  `design.md`, `tasks.md`, and delta `specs/`.
- The `.claude/skills` folder includes skills for proposing, applying, archiving, and
  exploring OpenSpec changes.
- The useful arcgentic pattern is a persistent spec artifact graph, not taking a Node CLI
  dependency.

## 3. V1 scope

### 3.1 In scope

- Add a source-intake model that records external workflow sources as auditable inputs.
- Add a capability-registry model for marketplace-style plugin catalogs.
- Add OpenSpec-style artifact governance for proposals, designs, tasks, delta specs, and
  archives.
- Map OpenSpec artifacts into arcgentic handoff and audit surfaces.
- Extend `plan-round` so V1 planning can read capability registry and spec artifacts.
- Extend `execute-round` so implementation tasks can be traced back to spec tasks.
- Extend audit checks so V1 release readiness verifies manifest/version/docs alignment.
- Publish v1.0.0 as a stable release only after dogfood gates pass.

### 3.2 Out of scope

- No hard dependency on the OpenSpec npm package.
- No vendoring or copying Superpowers Marketplace plugin code.
- No automatic installation of third-party plugins.
- No background marketplace polling.
- No paid API calls.
- No new hosted service.
- No broad UI/dashboard.
- No Moirai-specific rule names or project facts.

## 4. Architecture

```mermaid
flowchart LR
  ExternalSources["External Sources"] --> SourceIntake["source-intake"]
  SourceIntake --> CapabilityRegistry["capability-registry"]
  SourceIntake --> SpecGovernance["spec-governance"]

  CapabilityRegistry --> PlanRound["plan-round"]
  SpecGovernance --> PlanRound
  PlanRound --> ExecuteRound["execute-round"]
  ExecuteRound --> SelfAudit["self-audit handoff"]
  SelfAudit --> ExternalAudit["audit-round"]
  ExternalAudit --> ArchiveLessons["archive + lessons"]

  GateEngine["audit-check + quality gates"] --> PlanRound
  GateEngine --> ExecuteRound
  GateEngine --> ExternalAudit
```

## 5. New module seams

### 5.1 `source-intake`

Purpose: normalize external workflow sources into auditable records.

Interface:

- Input: repo URL, raw file URL, local path, or marketplace catalog path.
- Output: source record with `id`, `kind`, `origin`, `retrieved_at`, `revision`,
  `license`, `used_parts`, `excluded_parts`, and `rt_tier`.
- Error modes: inaccessible source, unsupported source kind, missing license, malformed
  catalog, duplicate source id.

Depth: medium. The interface hides fetch/parsing details while preserving enough evidence
for audits.

### 5.2 `capability-registry`

Purpose: parse marketplace-style catalogs and expose available capabilities to planning.

Interface:

- Input: source-intake record pointing to a marketplace JSON file.
- Output: capability list with `name`, `version`, `source`, `strict`, `category`,
  `description`, and normalized tags.
- Error modes: invalid JSON, missing plugin name, unsupported source type, duplicate
  capability identity.

Depth: real seam. There are at least two known adapters:

- Superpowers-style `.claude-plugin/marketplace.json`.
- Codex/OpenAI-style `.agents/plugins/marketplace.json`.

### 5.3 `spec-governance`

Purpose: represent OpenSpec-style changes without requiring OpenSpec CLI.

Interface:

- Input: `openspec/changes/<change>/` directory or arcgentic-native spec directory.
- Output: artifact graph containing proposal, design, tasks, delta specs, status, and
  archive target.
- Error modes: missing required artifact, dependency order violation, incomplete tasks,
  unsynced delta specs, archive conflict.

Depth: high. It gives arcgentic a spec artifact graph while keeping implementation
independent of one vendor CLI.

## 6. Artifact mapping

| OpenSpec artifact | arcgentic artifact | V1 behavior |
|---|---|---|
| `proposal.md` | handoff § problem / scope / non-scope | Planner must summarize proposal facts |
| `design.md` | handoff architecture / implementation strategy | Planner cites design decisions and alternatives |
| `tasks.md` | execute-round task list | Developer checks off tasks only after verification |
| `specs/*/spec.md` | audit requirement facts | Auditor verifies implemented behavior against spec |
| `archive/YYYY-MM-DD-*` | closed round archive | Lesson codifier can mine archived changes |

## 7. State-machine changes

V1 keeps the current round states. It adds optional metadata, not new mandatory states:

```yaml
current_round:
  source_intake:
    - id: superpowers-marketplace
      kind: marketplace
      rt_tier: RT0
  spec_change:
    name: arcgentic-v1-openspec-superpowers
    schema: spec-driven
    proposal: docs/specs/...
    design: docs/specs/...
    tasks: docs/specs/...
  capability_registry:
    path: docs/capabilities/registry.json
    count: 10
```

Reason: adding states for every spec phase would duplicate OpenSpec. arcgentic's state
machine should remain the enforcement layer for rounds, while spec-governance owns the
artifact graph.

## 8. Session Mode Gate

Before `awaiting_dev_start -> dev_in_progress`, arcgentic must force an explicit session
mode decision. This is a workflow entry seam, not a convenience prompt.

### 8.1 Mode A — single-session orchestrator

Current session identity: orchestrator.

Behavior:

- Orchestrator dispatches planner, developer, BA, CR, SE, lesson-codifier, and auditor
  sub-agents inside one session.
- Developer work may trigger audit automatically only if the sub-agent dispatch transport
  is mechanically verified.
- If dispatch fails or is unavailable, the workflow must degrade to manual verified
  execution and record the failure as an adapter finding. It must not claim full
  single-session automation.

### 8.2 Mode B — multi-session identity handoff

Current session identity: orchestrator/planner until handoff is complete.

Behavior:

- Orchestrator stops at `awaiting_dev_start`.
- Orchestrator emits a Dev Session identity prompt with handoff path, round id, allowed
  scope, required gates, and stop condition.
- User opens a separate developer session and pastes the identity prompt.
- After developer self-audit, orchestrator emits an Audit Session identity prompt.
- Audit session must not share developer role identity and must independently verify facts.

### 8.3 Required UX

At the mode gate, arcgentic must ask the user to choose:

- `single-session`: one session dispatches sub-agents and starts audit automatically after
  dev, if dispatch transport is verified.
- `multi-session`: current session stops and prints identity handoff prompts for separate
  dev/audit sessions.

No implementation work should begin before this gate is resolved.

## 9. CLI changes

Proposed commands:

```bash
arcgentic source-intake add <source> --kind marketplace|openspec|repo|doc
arcgentic capability-registry build --sources docs/source-intake/*.yaml
arcgentic spec-governance status <change-dir>
arcgentic spec-governance validate <change-dir>
arcgentic spec-governance archive <change-dir>
arcgentic session-mode prompt --round <round> --handoff <path>
arcgentic v1-release-readiness --repo-root .
```

Existing commands stay:

```bash
arcgentic audit-check
arcgentic validate-handoff
arcgentic quality-gate-enforce
arcgentic codify-lesson
arcgentic track-refs
arcgentic cross-session-handoff
```

## 10. Skill changes

### 10.1 New skill: `source-intake`

Trigger: when a user provides external workflows, reference repos, marketplace catalogs,
OpenSpec resources, or asks to fuse outside workflow material into a round.

Responsibilities:

- classify source tier;
- record source triplet;
- extract capability/spec facts;
- refuse direct dependency if a source is only RT0/RT1.

### 10.2 New skill: `spec-governance`

Trigger: when a round uses proposal/design/tasks/spec/archive artifacts.

Responsibilities:

- validate artifact graph;
- map proposal/design/tasks to handoff sections;
- surface incomplete tasks before audit;
- assess archive readiness.

### 10.3 New skill: `session-mode`

Trigger: when a round reaches `awaiting_dev_start`, when a user says "use the complete
arcgentic workflow", or when a developer/auditor session needs an identity handoff.

Responsibilities:

- declare the current session identity;
- ask the user to choose single-session or multi-session execution;
- verify whether single-session sub-agent dispatch is actually available;
- emit developer and auditor handoff prompts for multi-session mode;
- block dev start until mode is confirmed.

### 10.4 Updated skills

- `plan-round`: include source intake and capability registry in handoff.
- `execute-round`: check task traceability and require session-mode confirmation before
  implementation.
- `audit-round`: verify artifact facts and release-readiness facts.
- `track-refs`: optionally consume source-intake records.
- `codify-lesson`: mine archived spec changes.

## 11. Test strategy

### Unit tests

- Parse Superpowers-style marketplace JSON.
- Parse Codex-style local marketplace JSON.
- Detect duplicate capability names.
- Validate OpenSpec-style artifact directory.
- Count complete/incomplete tasks.
- Detect archive target collision.
- Validate source-intake record schema.
- Generate single-session and multi-session identity prompts.
- Refuse single-session auto-audit when dispatch transport is unavailable.

### Integration tests

- Source intake from local fixture marketplace -> capability registry.
- OpenSpec-style change fixture -> handoff validation.
- Tasks complete -> spec-governance archive-ready.
- Incomplete tasks -> archive warning or failure depending strict mode.
- V1 release readiness catches manifest/version README drift.
- `awaiting_dev_start` produces mode choices before `dev_in_progress`.

### Regression tests

- Existing 277 toolkit tests must remain passing.
- Existing Bash state/gate tests must remain passing.
- Plugin validator must pass for repo and installed local symlink.

## 12. Release gates

V1 stable requires:

- `pytest` green.
- `mypy --strict` green.
- `ruff check` green.
- Bash gate tests green.
- Codex plugin validator green.
- Claude plugin manifest present and version-aligned.
- Codex plugin manifest present and version-aligned.
- `plugin.json`, `toolkit/pyproject.toml`, `README.md`, `README.zh-CN.md`, marketplace
  metadata all say `1.0.0`.
- V1 dogfood round has a self-audit handoff and external verdict.
- No source-intake record references a source without license/status classification.
- Dogfood evidence includes which session mode was selected and why.

## 13. Risks

- Coupling risk: making OpenSpec CLI mandatory would violate arcgentic's local Python/Bash
  portability.
- Scope risk: marketplace integration could become plugin management. V1 only discovers
  and records capabilities.
- Audit risk: spec artifacts can become narrative-only. V1 must convert them into
  mechanical audit facts.
- Release risk: version surfaces have drifted before. V1 needs a dedicated release
  readiness gate.
- Identity risk: if the current session role is implicit, developer and auditor roles can
  contaminate each other. The session-mode gate must make identity explicit before dev.

## 14. Recommended implementation order

1. Add fixtures for marketplace catalogs and OpenSpec-style changes.
2. Implement session-mode prompt generation and mode gate.
3. Implement source-intake data model and validator.
4. Implement capability-registry parser.
5. Implement spec-governance artifact graph validator.
6. Add CLI commands around those modules.
7. Update `plan-round`, `execute-round`, and `audit-round` skills.
8. Add V1 release-readiness gate.
9. Update README/plugin manifests to `1.0.0-alpha.1`.
10. Dogfood arcgentic-on-arcgentic V1 round.
11. External audit and promote to `1.0.0` only after Gate 3 portability proof.

## 15. Open decisions

- Whether V1 stable requires live Claude Code plugin loading proof, or local validator proof
  is enough for the first V1 release candidate.
- Whether source-intake records should be YAML for readability or JSON for strict schema
  enforcement.
- Whether `spec-governance archive` should physically move directories or only validate
  archive readiness in v1.0.0.
- Whether single-session mode in Codex should use Codex thread tools, multi-agent tools, or
  be marked unavailable until a real dispatch adapter exists.
