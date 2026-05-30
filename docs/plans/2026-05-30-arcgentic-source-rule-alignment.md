# arcgentic source-rule alignment

**Date:** 2026-05-30  
**Purpose:** Align arcgentic's product target with the original Moirai session discipline captured in the three source-rule documents.

## 1. Source rules

| Source | Role | Portable arcgentic primitive |
|---|---|---|
| `/Users/archiesun/Desktop/Planning Rule.html` | Planning session: plan gate after external PASS | `plan-round` |
| `/Users/archiesun/Desktop/Dev Rule.html` | Dev session: execute handoff, self-audit, produce completion/audit handoff | `execute-round` |
| `/Users/archiesun/Desktop/External Audit Rule.html` | External audit session: independent PASS / NEEDS_FIX gate | `audit-round` |

These files are Moirai-specific, but the transferable product is not Moirai. The transferable product is a disciplined cross-session development workflow.

## 2. Product target

arcgentic helps a user move from requirement/concept to audited implementation faster by enforcing a round workflow:

1. User gives requirement and concept.
2. `plan+audit session` restores repo context and checks whether the previous round is PASS or NEEDS_FIX.
3. Planning scans relevant GitHub/reference projects and classifies how each reference may be used.
4. Planning scans available skills, MCP servers, connectors, plugins, and local tools.
5. Planning writes a markdown handoff that tells the dev session exactly what to build, what not to build, what refs/tools to use, how to verify, and when to stop.
6. User passes the handoff to `dev session`.
7. Dev session implements the round, self-audits, and writes completion/audit handoff information.
8. User passes the dev completion back to `plan+audit session`.
9. External audit returns exactly PASS or NEEDS_FIX.
10. PASS allows the next planning round. NEEDS_FIX allows only a narrow fix round.
11. `test session` is optional and exists only when a round has verification work that should be isolated from dev/audit context or environment.

## 3. Session boundaries

| Session | Responsibility | Must not do |
|---|---|---|
| `plan+audit session` | Plan next round after PASS; audit completed round; write handoff/fix handoff | Do dev implementation; hide next-round planning inside audit verdict |
| `dev session` | Execute handoff; self-audit; report completion | Expand scope; decide core contract while building; rely on live/paid/secret verification unless explicitly allowed |
| `test session` | Optional isolated verification surface | Exist by default; replace audit; broaden platform scope without round need |

## 4. Reference use modes

Planning must classify every selected reference with one use mode:

| Mode | Meaning | Required explanation |
|---|---|---|
| Direct use | Use as dependency, vendored component, or operator-installed tool | License, boundary, import/install path, test strategy |
| Rebuild | Borrow architecture/algorithm and reimplement in project style/language | Preserved interface ideas, discarded implementation details |
| Enhance | Use current project capability and add what the reference lacks | Enhancement point, compatibility risk, tests |
| Strengthen | Rewrite a performance/isolation-critical path in a stronger language | Requires explicit founder approval before implementation |
| Adapt | Modify reference idea/code for project fit | Diff intent, interface convergence, foreign architecture not copied blindly |
| Reference-only | Learn from it but do not bring code into the commit graph | Reason: license, mismatch, low fit, unknown provenance, or scope |

## 5. Handoff contract

Every planning handoff must contain:

1. Round identity and parent gate.
2. Why this round exists.
3. Allowed scope.
4. Forbidden scope.
5. Reference table with use modes.
6. Tooling plan: skills, MCP, connectors, plugins, local commands.
7. Implementation tasks.
8. Required tests.
9. Required audit facts.
10. Stop condition.
11. Devsession message.

The devsession message must be copyable markdown with:

```markdown
Read: <handoff path>
Start round: <round>
Allowed scope: <summary>
Forbidden scope: <summary>
Required references/tools: <summary>
Required verification: <summary>
Stop after: <commit + push + CI green + audit handoff + worktree clean>
```

## 6. Audit contract

External audit must:

1. Restore the repo state from committed evidence, not session memory.
2. Read the handoff, audited commit/range, changed files, CI status, and claimed verification.
3. Inspect implementation/tests when code changed.
4. Give exactly PASS or NEEDS_FIX.
5. Use P0/P1/P2/P3 severities.
6. Treat P0/P1/P2 as blockers unless explicitly downgraded by evidence.
7. Use immutable evidence for historical claims: fixed commit, fixed range, fixed CI run, or committed file at exact SHA.
8. On NEEDS_FIX, produce an executable narrow fix-round handoff.
9. On PASS, close the current round only; next-round planning belongs to planning.

## 7. Current main status

Current `main` at `b2627b7` is v0.1.0-alpha.2.

| Area | Status |
|---|---|
| State machine | Implemented MVP |
| `init.sh` / `pickup.sh` / `transition.sh` / schema validation | Implemented MVP |
| Handoff / commit-chain / verdict gates | Implemented MVP |
| `audit-round` skill | Implemented MVP |
| `orchestrate-round` skill | Implemented MVP |
| `pre-round-scan` skill | Implemented initial version |
| `plan-round` skill | Declared in manifest, missing from main files |
| `execute-round` skill | Declared in manifest, missing from main files |
| planner/developer/BA/CR/SE agents | Declared in manifest, missing from main files |
| Reference discovery/classification | Not productized |
| Optional isolated test session | Not productized |

Verification observed on 2026-05-30:

```text
9 test files, 0 failed
```

## 8. v0.2 candidate branch status

Branch/tag inspected:

```text
origin/claude/quirky-allen-abb31b
v0.2.0-alpha.1 -> d70a4e5
```

The branch is not merged into `main`. It adds a candidate v0.2 implementation:

| Area | Candidate status |
|---|---|
| `plan-round` | Added |
| `execute-round` | Added |
| planner/developer/BA/CR/SE agents | Added |
| handoff templates | Added |
| BA/self-audit/external verdict templates | Added |
| Python toolkit package | Added |
| IDE adapters | Added |
| `audit_check.py` | Added |
| hooks | Added |
| pytest suite | Added |

Verification observed on 2026-05-30 in the existing worktree at
`/Users/archiesun/Desktop/Arc Studio/arcgentic/.claude/worktrees/quirky-allen-abb31b`:

```text
toolkit pytest: 251 passed in 2.67s
toolkit mypy: Success: no issues found in 36 source files
toolkit ruff: All checks passed!
root bash tests: 10 test files, 0 failed
pre-commit hook test: 6 passed, 0 failed
```

Environment note: the default `python3` could import `yaml/jsonschema`, but lacked `pytest`, `mypy`, and `ruff`. Verification used a temporary toolkit-local `.venv` for test tools and `PYTHONPATH=src:/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages` for existing runtime dependencies. The `.venv` was removed after verification.

Known forward-debts recorded on that branch:

| ID | Severity | Meaning |
|---|---|---|
| ER-RETRY | P2 | execute-round lacks retry-with-context loops |
| ER-AUDIT-GATE-4 | P1 | execute-round audit-check integration staged as follow-up |
| ER-AUDIT-FACTS | P2 | self-audit mechanical fact table is still skeletoned |
| ER-STATE-ROW | P3 | project-specific state-row refresh is a no-op |

## 9. Gap analysis against source rules

| Source-rule capability | Main | v0.2 candidate | Remaining gap |
|---|---|---|---|
| Planning gate | Partial | Mostly present | Needs source-rule contract enforcement |
| Dev execution/self-audit | Partial/manual | Mostly present | Needs retry loops and audit fact generation |
| External audit gate | MVP present | Stronger | Needs immutable-evidence enforcement beyond prose |
| PASS / NEEDS_FIX loop | State-supported | State-supported | Needs complex fix-round dogfood |
| Reference use classification | Missing | Partial/templates | Needs schema + gate checks |
| Tooling scan | Initial skill | Initial/templated | Needs stronger inventory + used/considered/not-used accounting |
| Cross-session handoff | Manual | Partial | Needs copyable message protocol as first-class output |
| Optional test session | Missing | Missing | Needs trigger criteria + isolated handoff/result format |

## 10. Recommended next sequence

1. Decide whether to promote `origin/claude/quirky-allen-abb31b` / `v0.2.0-alpha.1` into `main`.
2. If promoted, fast-forward or merge the v0.2 candidate into `main`.
3. Keep the source-rule alignment document in the merge so future rounds do not regress to a narrower interpretation of arcgentic.
4. Open a new alignment round to convert this source-rule contract into enforceable schemas/gates:
   - reference use-mode schema
   - handoff required-field gate
   - audit immutable-evidence gate
   - optional test-session trigger/result schema
5. Defer P1/P2 work (`track-refs`, `codify-lesson`, `cross-session-handoff`) until the v0.2 baseline is reconciled with `main`.

## 11. Current verdict

`main` has a working v0.1 workflow kernel. The v0.2 candidate branch has now been mechanically verified in its existing worktree and implements the first full pass of plan/dev/audit role coverage, but it is not the current mainline. The product still needs source-rule alignment before it can honestly claim to implement the Moirai-derived workflow as a reusable arcgentic system.
