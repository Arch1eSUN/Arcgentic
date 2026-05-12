# RT0–RT3 reference tier taxonomy

Classify every external reference cited by **how the round uses it**. The tier determines what diligence the round owes.

## RT0 — Inspiration

**Definition**: read the reference, take only the *conceptual approach*, write nothing in Moirai/your-project that grep-matches the reference.

**Diligence owed**:
- License compatibility: doesn't matter (no code copied)
- Reference triplet: 用了什么部分 = "conceptual inspiration only; no code transfer"
- Audit check: no `references/<repo>/<sub-path>` strings appear in commit diff

**Example use case**:
- Read 5 multi-agent papers, design our own architecture combining ideas

## RT1 — Source adapt

**Definition**: pull specific code or patterns from the reference into your codebase, with adaptation (rewrite for typed errors, project conventions, etc.). Cite triplet with exact lines.

**Diligence owed**:
- License compatibility: MUST be compatible (MIT / Apache-2.0 / BSD / etc.)
- Attribution: top-of-file comment citing the reference + license
- Reference triplet: 用了什么部分 = specific lines or function names
- Audit check: license + attribution comment must be present in adapted file

**Example use case**:
- Adapt letta's Unicode surrogate regex into project's identifier guard

## RT2 — Binary subprocess vendor

**Definition**: ship a pre-built binary from the reference (not source). Your code spawns the binary as subprocess + communicates via stdin/stdout/files/HTTP. No source-level integration.

**Diligence owed**:
- License compatibility: MUST be compatible AND allow redistribution
- Binary integrity: SHA-256 checksums pinned in handoff + verified at install time
- Lifecycle: supervisor (start / health-check / restart / stop) — see Moirai's CliproxySupervisor pattern as canonical example
- Reference triplet: 用了什么部分 = binary name + version pinned
- Audit check: install script verifies checksum; binary lives under `<project>/vendor/` or similar; no source files copied

**Example use case**:
- Vendor cliproxy v7.0.3 Go binary, spawn as subprocess, communicate via HTTP

## RT3 — Full dependency

**Definition**: import the reference as a normal dependency (pip install / npm install / go get / etc.). Code uses the reference's public API.

**Diligence owed**:
- License compatibility: MUST be compatible
- Version pinning: exact version in dependency manifest
- Reference triplet: 用了什么部分 = imported modules + API surfaces called
- Audit check: dependency present in lock file with matching version

**Example use case**:
- `pip install jsonschema==4.20.0` and import jsonschema.Draft202012Validator

## Tier choice guidance

```
Need full library functionality? → RT3 (full dep)
Need specific code/pattern + project conventions? → RT1 (source adapt)
Need a feature that's a CLI tool / daemon? → RT2 (binary subprocess)
Just learning, no copy? → RT0 (inspiration)
```

## When tier is unclear

Default UP the tier ladder (RT0 → RT1 → RT2 → RT3). RT3 owes the most diligence; RT0 the least. Erring high means more diligence is done than necessary, which is safe. Erring low means diligence is skipped, which is unsafe.

## Audit fact (every round citing references)

```bash
| F | every reference has tier declared | cd <project> && grep -A 100 "## Reference scan" <handoff-doc> | grep -cE "RT[0-3]" | <reference-count> |
```

Expected value = number of references cited; if less, some references lack tier classification.

## Generalized rule (mandate-quotable)

> Every external reference cited must declare a tier (RT0 / RT1 / RT2 / RT3). Tier dictates diligence; never skip a tier's required check.
