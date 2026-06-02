# R1-v1-openspec-marketplace — BA Design Pass

## 1. Objective

Turn the V1 design contract into implementation decisions that keep arcgentic local-first,
testable, and mechanically auditable.

## 2. Decisions

### D-1: Source records use YAML files with Python dataclass validation

Decision: source-intake records are YAML for operator readability, then normalized into
typed Python dataclasses.

Rationale: arcgentic already uses YAML for `.agentic-rounds/state.yaml`; source records
are operator-facing audit artifacts, not machine-only build products.

Alternative rejected: JSON-only records. JSON is stricter but worse for hand-authored
audit/source records.

### D-2: Capability registry output is JSON

Decision: capability-registry produces JSON because it is generated machine output and
will be consumed by CLI gates and release-readiness checks.

Rationale: generated registries benefit from deterministic JSON ordering and direct
schema-style assertions in tests.

Alternative rejected: Markdown registry. It is readable but weaker as a test surface.

### D-3: Spec governance archive is validate-only in V1

Decision: V1 validates archive readiness and collision status but does not move directories.

Rationale: physical archive moves are destructive. V1's first stable release should prove
the artifact graph before mutating OpenSpec-style directories.

Alternative rejected: moving `openspec/changes/<name>` into `archive/` immediately. Useful
later, but too destructive for first integration.

### D-4: Capability tags are explicit-first with conservative inference

Decision: use explicit `keywords`, `category`, or metadata tags when present; otherwise
derive a small tag set from the plugin name and description.

Rationale: marketplace catalogs do not consistently expose tags. Conservative inference
keeps planning useful without pretending the source declared more than it did.

Alternative rejected: no inferred tags. That makes registries less useful for planning.

### D-5: V1 release readiness checks installed-local shape

Decision: v1-release-readiness verifies the local Codex install shape only when the paths
exist. It must not require every user to have the same `/Users/archiesun/plugins` setup.

Rationale: local install proof is valuable for dogfood, but global release gates must remain
portable.

Alternative rejected: hard-code user-local paths as mandatory release requirements.

### D-6: Session mode is an explicit pre-dev gate

Decision: `awaiting_dev_start` must force a mode choice before implementation begins:
single-session orchestrator with verified sub-agent dispatch, or multi-session identity
handoff with separate developer and auditor sessions.

Rationale: arcgentic's audit independence depends on explicit role identity. If the current
session silently becomes founder, planner, developer, and auditor, the workflow loses the
property it claims to enforce.

Alternative rejected: infer mode from the user saying "use full workflow". That phrase
does not say whether the user wants one orchestrator session or multiple identity-scoped
sessions.

### D-7: Mode choice is preceded by a recommendation classifier

Decision: the system recommends single-session or multi-session before asking the user to
choose.

Rationale: users should not need to infer process weight manually. Lightweight local work
should default toward one orchestrated session; long-running, release-sensitive, workflow,
security, or cross-role work should default toward multi-session identity separation.

Alternative rejected: always ask a raw binary choice. It is explicit, but it shifts process
analysis onto the user and weakens arcgentic's guidance value.

### D-8: Agency catalogs provide role families, not imported agents

Decision: parse agency-agents-style catalogs as role-family references for identity prompts.
Do not import all upstream role files into arcgentic.

Rationale: arcgentic needs role routing and identity handoff, not another bundled catalog of
hundreds of prompts. Keeping roles as references preserves locality and avoids prompt bloat.

Alternative rejected: vendoring `agency-agents` and `agency-agents-zh` roles into arcgentic.
That would create a large sync burden and blur arcgentic's planner/developer/auditor model.

## 3. Module Boundaries

- `source_intake.py`: source record parsing and validation.
- `capability_registry.py`: marketplace catalog parsing and registry generation.
- `spec_governance.py`: OpenSpec-style artifact graph validation.
- `v1_release.py`: version/install/readiness checks.
- `session_mode.py`: pre-dev mode prompt and identity handoff generation.
- `agency_roster.py`: agency-agents-style role catalog parsing and role-family selection.

The modules stay independent. `v1_release.py` may call the other modules; the others must
not import release-readiness code.

## 4. Testing Contract

Each module gets focused unit tests. Integration happens through CLI tests, not by mocking
arcgentic's own modules.

## 5. BA Risk Notes

- Adapter transport failure is not fixed in this round unless it blocks release-readiness
  implementation. It remains a recorded V1 forward debt.
- No source parser should fetch remote URLs during tests.
- Fixtures must be synthetic and local.

*BA design pass written inline after adapter dispatch failure; verified local execution path applies.*
