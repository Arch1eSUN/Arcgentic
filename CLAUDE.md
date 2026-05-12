# Arcgentic v0.2.0 — Dev Session Handoff

> **This file is auto-loaded by Claude Code at session start.** Read fully before any action. This is your single source of orientation for executing arcgentic v0.2.0.

---

## 1. Identity

You are a **dev session** continuing arcgentic development.

- **Previous milestone:** v0.1.0-alpha.2 MVP, tagged @ `2efea61` on `main`, fully pushed to `origin/main`. See `CLAUDE-v0.1.0-handoff.md` for that session's context (archived).
- **Current milestone:** v0.2.0 — full role coverage (the P0 group in spec § 19.3 three-phase split).
- **Build contract for this session:** [`docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md`](docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md) (3366 LOC / 23 sections, self-contained — read in full before Task 1).

You execute the spec end-to-end for the **P0 release only** (v0.2.0 release; ~18h estimated). P1 (v0.2.1) and P2 (v0.2.2) are out of scope for this session.

---

## 2. NOT-this (boundary)

| Boundary | Why it matters |
|---|---|
| **NOT Moirai** (`~/Desktop/Arc Studio/Moirai/`) | arcgentic is a separate plugin. Do not touch Moirai files. Do not commit to Moirai repo. (Spec § 23 cites Moirai as origin — that does NOT grant write access.) |
| **NOT v0.1.0-alpha.2 rebuild** | v0.1.0 is closed. Tag `v0.1.0-alpha.2` @ `2efea61` is published. Do not rewrite v0.1.0 history; do not amend any commit prior to HEAD-of-this-session. |
| **NOT v0.2.1 (P1) work** | Per spec § 19.3: P1 = `codify-lesson` skill + `track-refs` skill + `lesson-codifier` + `ref-tracker` agents. These ship in v0.2.1, NOT v0.2.0. |
| **NOT v0.2.2 (P2) work** | Per spec § 19.3: P2 = `cross-session-handoff` skill. Ships in v0.2.2. |
| **NOT a planner role** | Spec is already a plan-level document (more detailed than v0.1.0's plan). Your job is execution, not plan-writing. If you find a spec gap → surface to founder; do NOT silently expand. |
| **NOT an auditor role** | External audit happens after v0.2.0 ships. This session executes only. |
| **NOT IDE adapter beyond spec § 3** | Spec § 3 defines `IDEAdapter` Protocol + 4 implementations. Do not invent new adapters for Cursor variants / JetBrains / etc. — that's v0.3+ scope. |

---

## 3. Where you are (state as of handoff)

| Item | Value |
|---|---|
| Repo local | `/Users/archiesun/Desktop/Arc Studio/arcgentic/` |
| Repo remote | `git@github.com:Arch1eSUN/Arcgentic.git` (PUBLIC) |
| Branch | `main` (tracking `origin/main`) |
| HEAD at handoff | (will be updated by the next commit — this CLAUDE.md rotation commit) |
| Most recent tag | `v0.1.0-alpha.2` @ `2efea61` (annotated, pushed) |
| Total commits in repo | ~38 (10 pre-MVP + 28 MVP arc since scaffold `70b6773`) |
| Test files | 9 (`scripts/**/*.test.sh` + `tests/integration/full-lifecycle.test.sh`) — 48 assertions, 100% PASS as of v0.1.0-alpha.2 close |
| Plan file (this session) | [`docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md`](docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md) (3366 LOC) |
| Prior plan (reference) | [`docs/plans/2026-05-12-arcgentic-mvp-plan.md`](docs/plans/2026-05-12-arcgentic-mvp-plan.md) (4580 LOC, COMPLETED) — read for historical patterns; do NOT re-execute |

### v0.1.0-alpha.2 inventory (already in repo — do NOT recreate)

```
plugin.json (version "0.1.0-alpha.2"; status reflects MVP completion)
README.md (updated for alpha.2 + dogfood Gate 1/2 PASS narrative)
README.zh-CN.md (still on alpha.1 — TODO: sync if you touch README in v0.2.0)
LICENSE
.gitignore (includes .claude/ + .agentic-rounds/ + references/ + tracked-skill-references negations)
schema/state.schema.json (minLength on current_round.id removed per Phase 1 plan-bug fix)
scripts/test-helpers.sh
scripts/lib/{yaml.sh, state.sh}
scripts/state/{init.sh, validate-schema.sh, transition.sh, pickup.sh}.sh + .test.sh
scripts/gates/{handoff-doc-gate.sh, round-commit-chain-gate.sh, verdict-fact-table-gate.sh}.sh + .test.sh
tests/integration/full-lifecycle.test.sh
tests/dogfood/replay-r10-l3-llm/RESULT.md
tests/dogfood/gate-2-live-run/RESULT.md
tests/dogfood/gate-3-cross-project/PROTOCOL.md
docs/examples/state.example.yaml
docs/plans/v0.1.0-alpha.2-meta-handoff.md (Gate 2 dogfood artifact)
docs/audits/v0.1.0-alpha.2-meta-external-audit-verdict.md (Gate 2 dogfood artifact)
docs/plans/2026-05-12-arcgentic-mvp-plan.md (MVP plan, COMPLETED)
docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md (this session's build contract)
skills/using-arcgentic/SKILL.md
skills/pre-round-scan/SKILL.md + references/scan-checklist.md
skills/verify-gates/SKILL.md + references/gate-script-catalog.md
skills/audit-round/SKILL.md + references/{verdict-template, fact-table-design, lesson-codification-protocol, fix-example-vs-contract, sibling-doc-sweep, doc-vs-impl-regrep, reference-triplet, rt-tier-taxonomy}.md
skills/orchestrate-round/SKILL.md + references/{state-machine-overview, sub-agent-dispatch, single-vs-multi-session}.md
agents/auditor.md
agents/orchestrator.md
CLAUDE-v0.1.0-handoff.md (this file's predecessor, archived)
CLAUDE.md (this file)
```

### Files to be created (v0.2.0 P0 scope, per spec § 18)

Summary from spec § 18:
- `arcgentic/adapters/{base.py, claude_code.py, cursor.py, vscode_codex.py, codex_cli.py, __init__.py}` (IDE adapter layer)
- `arcgentic/skills/plan-round/{SKILL.md, planner_prompt.py, handoff_template_18.md, handoff_template_12.md, handoff_template_10.md, references/...}`
- `arcgentic/skills/execute-round/{SKILL.md, ba_brief.py, cr_brief.py, se_brief.py, finalization.py, references/...}`
- `arcgentic/agents/{planner.md, developer.md, ba-designer.md, cr-reviewer.md, se-contract.md}`
- `arcgentic/hooks/{pre-commit-fact-check.sh, round-boundary-lesson-scan.sh, quality-gate-enforce.sh}` (the 3 hooks)
- `arcgentic/audit_check.py` (Python reference impl per spec § 14.4, ~250 LOC)
- `arcgentic/scripts/fetch-references.sh`
- Tests for each above
- Updated `plugin.json` (skills list adds plan-round + execute-round; agents list adds 5 new; version bump to `0.2.0-alpha.1`)
- Updated `README.md` (status block reflects v0.2.0)

**Exact paths + line counts: see spec § 18.**

---

## 4. Your job

**Execute spec § 19 implementation order for v0.2.0 P0 only**, in the dependency order specified by spec § 19.2.

Per spec § 19.3:

| Sub-phase | Scope | Estimated time |
|---|---|---|
| **a. IDE adapter foundation** | adapters/base + 4 implementations + detect_adapter | 3–4h |
| **b. plan-round** | SKILL + planner agent + 3 handoff templates + tests | 5–6h |
| **c. execute-round** | SKILL + developer agent + ba-designer + cr-reviewer + se-contract + 4-commit chain + inline finalization + tests | 8–9h |
| **d. audit_check.py + 3 hooks** | per spec § 14.4 + § 6 | 2–3h |
| **e. v0.2.0 release housekeeping** | plugin.json bump + README + dogfood Gate 2 round (same pattern as v0.1.0-alpha.2-meta) + tag v0.2.0-alpha.1 | 2-3h |

**Total: ~20–25h.** Acceptance criteria per skill: spec § 20.

---

## 5. Read first (in this order, before sub-phase a)

1. **`CLAUDE.md`** (this file) — orientation (you're doing it now)
2. **[`docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md`](docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md)** — THE BUILD CONTRACT. Read fully, especially:
   - § 0 (scope + reading order)
   - § 1 (8 foundational principles)
   - § 2 (16-term domain vocabulary)
   - § 3 (IDE adapter — start here for sub-phase a)
   - § 5 (5 P0+P1+P2 agents — read planner / developer / ba-designer / cr-reviewer / se-contract entries for sub-phase c)
   - § 19 (implementation order + dependency graph — your task structure)
   - § 20 (acceptance criteria — your verification checklist)
3. **`plugin.json`** — current declared skills + agents list (8 of 10 skills + 2 of 9 agents implemented; v0.2.0 adds 2 skills + 5 agents)
4. **`schema/state.schema.json`** — state.yaml schema (current); may need extension for `4-commit chain` field + ba_design_doc + self_audit_doc fields per spec § 13
5. **`CLAUDE-v0.1.0-handoff.md`** — for historical context on Phase 1-4 patterns + plan-bug discoveries
6. **`docs/plans/2026-05-12-arcgentic-mvp-plan.md` § Completion Record** — final state of v0.1.0; do not re-execute, only reference

---

## 6. Inherited discipline (non-negotiable)

These survived v0.1.0-alpha.2 dogfood and are mandatory for v0.2.0:

### 6.1 Cost discipline (from spec § 1 principle 1 + 1.4)

- ❌ NO paid-API calls from any plugin code (no OpenAI / Anthropic API / Gemini / Cohere SDK / etc.)
- ❌ NO background processes / daemons / cron triggers — everything foreground + on-demand
- ❌ NO auto-pull from cloud LLMs as part of "normal flow"
- ✅ All LLM reasoning happens in your Claude Code subscription
- ✅ If a task tempts you to add paid-API integration "for convenience" → refuse; surface to founder

### 6.2 Spec-as-contract (stricter than v0.1.0's plan-as-contract)

The spec is **denser** than v0.1.0's plan — it includes reference implementations (audit_check.py ~250 LOC), full templates (handoff 18/12/10-section), and mechanical acceptance criteria. Treat it as:

- **Follow sub-phases in order.** Sub-phase b outputs (planner agent, handoff templates) feed sub-phase c (execute-round consumes handoffs).
- **Do not extend scope.** Spec § 19.3 explicitly splits P0/P1/P2. Do NOT silently merge P1 or P2 work into v0.2.0. If you find P1/P2 worth doing → surface as forward-debt; do not implement.
- **Do not skip spec steps.** Each acceptance criterion in § 20 is a mechanical check — they're the contract for v0.2.0 PASS.
- **Plan-bug fix policy** (inherited from v0.1.0): local spec bugs → silently fix + commit-body `Spec note:` paragraph; cascade spec bugs → surface to founder.

### 6.3 TDD where applicable

- Bash scripts (hooks + adapters/*.sh): write failing test → run (see fail) → write impl → run (see pass) → commit.
- Python files (audit_check.py + ba_brief.py etc.): write pytest → run (see fail) → impl → run (see pass) → commit. Spec § 21 has test fixtures.
- Markdown skills/agents: write → invoke `plugin-dev:skill-reviewer` or `plugin-dev:agent-creator` validation if available → fix → commit.

### 6.4 Commit discipline (same as v0.1.0)

- **One commit per sub-phase task** (or per 2-3 closely-related — e.g. ba-designer + cr-reviewer + se-contract may share one commit since they're co-designed).
- **Commit message format**: conventional-commits prefix (`feat(adapter):` / `feat(skill):` / `feat(agent):` / `chore:` / `docs:` / `test:`) + 1-line summary + body explaining *why* + `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Direct commit on `main`**. NO branches / PRs / merge for solo work (founder's main-direct workflow preference — same as v0.1.0).
- **Push after each sub-phase boundary** to `origin/main`.

### 6.5 Anthropic SKILL.md conventions (same as v0.1.0)

YAML frontmatter:
```yaml
---
name: <skill-name-kebab-case>
description: <trigger-shaped sentence describing when Claude should load this skill>
---
```
Description = trigger condition, not capability description.

### 6.6 Trust-but-verify on sub-agent output (same as v0.1.0)

If you dispatch a sub-agent:
- Don't trust the success report
- Read the actual file written
- Run any claimed mechanical verifications yourself
- Then advance state

Sub-agents in v0.2.0 dev:
- For TDD-style file writes: `general-purpose` sub-agent + sonnet model (proven pattern from v0.1.0)
- For SKILL.md / agent.md writes: `general-purpose` + sonnet (proven)
- For longer multi-file work: dispatch can save context but verify line-by-line

### 6.7 SE CONTRACT-ONLY isolation is LOAD-BEARING (spec § 5.5.1)

**This is the most critical new mandate in v0.2.0.** Per spec § 5.5.1:

> SE (Software Engineer Contract) agent MUST NOT receive BA design doc as input. Contracts and tests are derived from handoff doc § 2-7 ONLY. This is mandate #20 enforcement.

When dispatching `se-contract` sub-agent:
- ❌ Do NOT include BA design doc path or content in the prompt
- ❌ Do NOT include CR review output
- ✅ Include handoff doc + scope section excerpt only
- ✅ Validate post-return: `se-contract` agent did not reference BA-design-only fields

Verify via grep on the produced contract: no BA-only vocabulary (e.g., specific implementation class names, design rationale phrases). If found → revoke; re-dispatch with stricter brief.

---

## 7. Execution mode

Same options as v0.1.0:

### Option A — Subagent-driven (recommended; proven in v0.1.0)

Invoke `superpowers:subagent-driven-development`. Each sub-phase task → fresh sub-agent. Review between tasks. Catches integration bugs early.

### Option B — Inline execution

Invoke `superpowers:executing-plans`. Walk sub-phases inline with sub-phase-boundary checkpoints.

**If founder hasn't specified at session start**: ask ONCE — "执行模式: subagent-driven (推荐) 还是 inline?" — then proceed without re-asking.

---

## 8. Communication protocol

### 8.1 During execution (same as v0.1.0)

- Use **TodoWrite** to track progress (mark `in_progress` before sub-phase task, `completed` after).
- **At sub-phase boundaries**: report briefly to founder (3-5 lines, Chinese). Format: *"Sub-phase X 完成。Y 个文件 / Z 个 test。下一步 Sub-phase X+1。"*
- **Mid-sub-phase**: silent execution. Don't narrate every commit.

### 8.2 On completion

When v0.2.0 P0 is complete (sub-phases a-e done, tag v0.2.0-alpha.1 created, pushed):
- Write a single completion summary (≤ 30 lines, Chinese):
  - Final HEAD commit + tag
  - Test count (all passing)
  - Sub-phase outcomes
  - Spec-bug findings (if any)
- Tag = `v0.2.0-alpha.1` (NOT `v0.2.0` stable — that's after dogfood)

### 8.3 On blocker (same as v0.1.0)

If you can't proceed:
- Surface IMMEDIATELY (don't bury in trying-stuff)
- Report: exact error + state.yaml current state + what you tried + what you need
- Do **NOT** auto-retry the same failing operation > 2 times
- Do **NOT** work around blockers by going off-spec

---

## 9. Acceptance criteria — when you're "done"

Per spec § 20 + v0.1.0 mechanical checks:

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"

# Check 1: spec § 20 acceptance per skill (5 sub-checks)
# (refer to spec § 20 for the exact 5 mechanical commands per skill)

# Check 2: all tests pass (v0.1.0 9 + v0.2.0 new tests)
TOTAL=0; FAIL=0
for f in $(find scripts tests arcgentic -name '*.test.sh' -o -name 'test_*.py'); do
  bash "$f" 2>/dev/null || FAIL=$((FAIL+1))
  TOTAL=$((TOTAL+1))
done
echo "$TOTAL test files, $FAIL failed"  # expect "<N> test files, 0 failed"

# Check 3: plugin.json version bumped
grep '"version"' plugin.json  # expect "0.2.0-alpha.1"

# Check 4: tag created
git tag -l 'v0.2.0-alpha.1'  # expect "v0.2.0-alpha.1"

# Check 5: skills list includes plan-round + execute-round
python3 -c "import json; m=json.load(open('plugin.json')); print('plan-round' in m['skills'], 'execute-round' in m['skills'])"
# expect "True True"

# Check 6: agents list includes 5 new agents
python3 -c "import json; m=json.load(open('plugin.json')); a=m['agents']; print(all(x in a for x in ['planner','developer','ba-designer','cr-reviewer','se-contract']))"
# expect "True"

# Check 7: dogfood Gate 2 (v0.2.0-alpha.1-meta round) closed PASS
test -f tests/dogfood/gate-2-v0.2.0/RESULT.md && echo "Gate 2 documented"
# expect "Gate 2 documented"

# Check 8: pushed to origin
git log origin/main..HEAD  # expect empty (everything pushed)
```

When all 8 checks pass: report completion to founder.

---

## 10. Hard NOs (do not under any circumstances)

| # | Rule | Why |
|---|---|---|
| 1 | Do NOT cd into / commit to / push to Moirai repo | arcgentic + Moirai are separate; cross-contamination breaks discipline |
| 2 | Do NOT change spec scope without founder approval | Spec is the contract |
| 3 | Do NOT add paid-API integrations | § 6.1 cost discipline |
| 4 | Do NOT do v0.2.1 (P1) or v0.2.2 (P2) work | Separate releases per spec § 19.3 |
| 5 | Do NOT rewrite v0.1.0 history (amend / rebase / force-push pre-handoff commits) | v0.1.0 is closed |
| 6 | Do NOT skip writing tests | TDD discipline |
| 7 | Do NOT force-push to main | Destructive; never without explicit permission |
| 8 | Do NOT pass BA design doc to SE agent | § 6.7 mandate #20 enforcement |
| 9 | Do NOT add files outside `~/Desktop/Arc Studio/arcgentic/` | Stay in your workspace |
| 10 | Do NOT install dependencies that aren't in spec § 17 quality gates list | (Bash + Python3 + PyYAML + jsonschema + mypy + pytest + ruff only) |
| 11 | Do NOT poll founder availability | They check in; don't interrupt |
| 12 | Do NOT use `--no-verify` / `--no-gpg-sign` on commits | Honor hooks; if a hook fails, fix the cause |

---

## 11. Environment (extended from v0.1.0)

| Component | Required version | Notes |
|---|---|---|
| Bash | ≥ 4 | Already installed via brew (`/opt/homebrew/bin/bash` = 5.3.9) from v0.1.0 prep |
| Python 3 | ≥ 3.8 | `/opt/anaconda3/bin/python3` = 3.13.5 |
| Python packages | PyYAML + jsonschema (existing) + **mypy** + **pytest** + **ruff** (NEW per spec § 17) | `python3 -m pip install --user PyYAML jsonschema mypy pytest ruff` |
| Git | any recent | |
| gh CLI | any recent | |
| Claude Code | ≥ 1.0 | |
| `superpowers` plugin | required | For subagent-driven-development / executing-plans / verification-before-completion |
| `plugin-dev` plugin | recommended | For skill-reviewer + agent-creator + plugin-validator quality gates |

**Verify environment before sub-phase a**:

```bash
bash --version | head -1                              # expect "GNU bash, version 5.x"
python3 --version                                     # expect "Python 3.x" ≥ 3.8
python3 -c "import yaml, jsonschema; print('a-ok')"   # expect "a-ok"
python3 -c "import mypy, pytest, ruff; print('b-ok')" # expect "b-ok"  (NEW — pip install if fails)
git remote -v                                         # expect "origin git@github.com:Arch1eSUN/Arcgentic.git"
gh auth status                                        # expect "Logged in to github.com"
```

---

## 12. Founder communication (same as v0.1.0)

| Detail | Value |
|---|---|
| Founder name | archiesun |
| Founder preferred chat language | 中文 (Chinese); code / git / files in English |
| Founder reachability | Periodic chat check-ins; do NOT poll their availability |
| Founder is also working on | (unknown; assume independent — don't try to coordinate via memory) |

**Founder-friendly status reports** are 3-5 lines, in Chinese, factual:
> "Sub-phase b 完成。plan-round skill + planner agent + 3 个 handoff template，11 个文件 / 8 个 test 全过。下一步 sub-phase c (execute-round + 4 agents)。"

NOT:
> "I successfully completed sub-phase b with great care, ensuring all..."

---

## 13. Origin (context — read once, then forget)

You are inheriting work from a previous Claude Opus 4.7 **v0.1.0-alpha.2 build session** that:

1. Executed v0.1.0-alpha.2 MVP per a 4580-line plan (the predecessor of this spec)
2. Surfaced 3 plan bugs during execution (test-helpers cascade + 2 inline plan notes); all fixed with commit-body documentation
3. Ran dogfood Gate 1 (structural-fidelity replay against Moirai R10-L3-llm) → STRUCTURAL PASS
4. Ran dogfood Gate 2 (live run on arcgentic-on-arcgentic version-bump round) → PASS, all 3 mechanical gates fired
5. Tagged `v0.1.0-alpha.2` annotated @ `2efea61`
6. Wrote `CLAUDE-v0.1.0-handoff.md` (this file's predecessor, archived)
7. Founder authored the v0.2.0 spec (this session's build contract) post-v0.1.0-tag

That session is **closed**. You are a **fresh dev session** with no inherited conversation context. The spec is the contract — execute it.

Read `CLAUDE-v0.1.0-handoff.md` if you need historical context about Phase 1-4 patterns (TDD discipline, plan-bug fix policy, Gate 1/2 dogfood structure). But do not re-execute v0.1.0 tasks — they are committed.

---

## 14. First action when this session starts

```
1. Read this CLAUDE.md fully (you're doing it now)
2. Run environment verification (§ 11)
3. Read `plugin.json` + `README.md` (current state)
4. Read `docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md` (full spec — 3366 LOC, ~30-45min)
   Priority sections: § 0, § 1, § 2, § 3, § 5 (planner/developer entries), § 19, § 20
5. Read `CLAUDE-v0.1.0-handoff.md` skim (or jump to specific § if a question arises about v0.1.0 history)
6. Ask founder: "执行模式: subagent-driven (推荐) 还是 inline?"
7. After founder answers: invoke the corresponding superpowers skill + begin sub-phase a (IDE adapter foundation)
```

---

## 15. End-state

When you're done with v0.2.0 P0:
- Tag `v0.2.0-alpha.1` exists, pushed to origin
- All 8 § 9 mechanical checks pass
- Sub-phase RESULTs documented (e.g., `tests/dogfood/gate-2-v0.2.0/RESULT.md`)
- This `CLAUDE.md` will be replaced by a v0.2.1 handoff (mirror of how v0.1.0's CLAUDE.md was replaced by this one)
- The v0.1.0-alpha.2 handoff continues to live as `CLAUDE-v0.1.0-handoff.md`; in v0.2.x release this file will become `CLAUDE-v0.2.0-handoff.md` (one archive per release)

Until then: this is your orientation. Read it, internalize it, then execute.

The spec is comprehensive — trust it. The v0.1.0 dogfood proved the foundation works. Now you're filling in the role coverage.

Good luck.
