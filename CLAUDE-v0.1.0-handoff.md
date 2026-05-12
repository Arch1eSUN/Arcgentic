# Arcgentic — Dev Session Handoff

> **This file is auto-loaded by Claude Code at session start.** Read fully before any action. This is your single source of orientation for continuing arcgentic plugin development.

---

## 1. Identity

You are a **dev session** continuing the development of **arcgentic** — a Claude Code plugin that turns four-role engineering discipline into a mechanically-enforced agentic harness.

This is **NOT** a fresh project. There is already:
- A 4-commit git history at `git@github.com:Arch1eSUN/Arcgentic.git`
- A complete 4580-line build contract at `docs/plans/2026-05-12-arcgentic-mvp-plan.md`
- A scaffold (plugin.json + README.md + README.zh-CN.md + LICENSE + .gitignore + schema/state.schema.json)
- An English + Chinese README + populated GitHub repo description + topics

Your job: **execute the build contract end-to-end** to land the MVP four-pack (Tasks 1-30).

---

## 2. NOT-this (boundary)

| Boundary | Why it matters |
|---|---|
| **NOT Moirai** (`~/Desktop/Arc Studio/Moirai/`) | arcgentic is a separate plugin distilled FROM Moirai patterns but is its own project. Do not touch Moirai files. Do not commit to Moirai repo. |
| **NOT a planner role** | The plan is done. You execute. If you find a plan gap → surface to founder, don't silently expand scope. |
| **NOT an auditor role** | An external auditor will validate after MVP completion (Gate 1 + Gate 2 dogfood). You don't audit yourself. |
| **NOT v0.2+ work** | After v0.1.0-alpha.2 MVP completes, STOP. v0.2 (remaining 6 skills + 7 agents) is a separate plan, not yet written. |

---

## 3. Where you are (state as of handoff)

| Item | Value |
|---|---|
| Repo local | `/Users/archiesun/Desktop/Arc Studio/arcgentic/` |
| Repo remote | `git@github.com:Arch1eSUN/Arcgentic.git` (PUBLIC) |
| Branch | `main` (tracking `origin/main`) |
| HEAD | `d7da73c` (Chinese README mirror commit) |
| Total commits | 4 (`825c233` init → `70b6773` scaffold → `f58526e` plan → `d7da73c` Chinese README) |
| Tag | (none — `v0.1.0-alpha.2` will be tagged at Task 29 per plan) |
| Plan file | `docs/plans/2026-05-12-arcgentic-mvp-plan.md` (4580 lines, 30 tasks, 4 phases) |
| Tests | (none yet — Task 1 introduces test framework) |

### Files already present (do NOT recreate)

```
.gitignore
LICENSE
README.md
README.zh-CN.md
plugin.json
schema/state.schema.json
docs/plans/2026-05-12-arcgentic-mvp-plan.md
CLAUDE.md  (this file)
```

### Files to be created (Tasks 1-30)

See plan § File Structure. Summary:
- `scripts/` (~17 Bash files including tests)
- `tests/integration/full-lifecycle.test.sh`
- `tests/dogfood/{replay-r10-l3-llm, gate-2-live-run, gate-3-cross-project}/`
- `skills/{using-arcgentic, pre-round-scan, orchestrate-round, audit-round, verify-gates}/SKILL.md` + each skill's `references/` subdir
- `agents/{orchestrator,auditor}.md`
- `docs/examples/state.example.yaml`

---

## 4. Your job

**Execute every task in `docs/plans/2026-05-12-arcgentic-mvp-plan.md`**, in order, phase by phase:

| Phase | Tasks | Scope | Estimated time |
|---|---|---|---|
| **Phase 1** | 1–11 | Bash test framework + state-machine scripts + 3 gate scripts + integration test (all TDD) | 3–5 hours |
| **Phase 2** | 12–22 | 5 SKILL.md files + 12 reference docs (Moirai patterns distilled portable) | 4–6 hours |
| **Phase 3** | 23–24 | 2 platform-neutral sub-agent definitions | 1–2 hours |
| **Phase 4** | 25–30 | 3 dogfood gates + plugin.json bump + README update + tag v0.1.0-alpha.2 | 2–4 hours |

**Total: ~10–15 hours of focused work.** The plan has explicit Phase checkpoints between phases — stop and validate before crossing each.

---

## 5. Read first (in this order, before Task 1)

1. **`plugin.json`** — the plugin manifest. Memorize the planned skill + agent inventory.
2. **`README.md`** — public-facing description of what arcgentic is. Understand the user-facing promise.
3. **`schema/state.schema.json`** — data structure of `state.yaml`. Reference for every state-script task.
4. **`docs/plans/2026-05-12-arcgentic-mvp-plan.md`** — the BUILD CONTRACT. Read fully. Reread Task 1 before starting.
5. *(Optional)* `README.zh-CN.md` if your primary language is Chinese.

---

## 6. Inherited discipline (non-negotiable)

### 6.1 Cost discipline

- ❌ **NO paid-API calls** from any plugin code (no OpenAI / Anthropic API / Gemini / Cohere SDK / etc.)
- ❌ **NO background processes / daemons / cron triggers** — everything foreground + on-demand
- ❌ **NO auto-pull from cloud LLMs** as part of "normal flow"
- ✅ All LLM reasoning happens in your Claude Code subscription
- ✅ If a task tempts you to add paid-API integration "for convenience" → refuse; surface to founder

### 6.2 Plan-as-contract

- **Follow tasks in order.** Task N's outputs are inputs to Task N+1.
- **Do not extend scope.** If you see something out of plan worth doing, log it as a forward-debt note + surface to founder; do NOT silently add it.
- **Do not skip task steps.** Each task's "Run test", "Verify", "Commit" steps are part of the contract.

### 6.3 TDD where applicable

- Bash scripts in Phase 1: write failing test → run (see fail) → write impl → run (see pass) → commit.
- SKILL.md / agent.md in Phase 2-3: write → invoke `plugin-dev:skill-reviewer` if available → fix → commit.

### 6.4 Commit discipline

- **One commit per task** (or per 2-3 closely-related tasks, e.g. Task 19's 2 mistake-pattern docs).
- **Commit message format**: conventional commits prefix (`feat(scripts):` / `feat(skill):` / `chore:` / `docs:` / `test:`) + 1-line summary + body explaining *why* + `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Direct commit on `main`**. NO branches / PRs / merge for solo work (founder's main-direct workflow preference).
- **Push after each Phase boundary** to `origin/main`.

### 6.5 Anthropic SKILL.md conventions

Every SKILL.md must have YAML frontmatter:
```yaml
---
name: <skill-name-kebab-case>
description: <trigger-shaped sentence describing when Claude should load this skill>
---
```

Description must be **trigger-shaped** — state the conditions under which the skill applies, not just what it does. Examples in the plan's reference SKILL.md content.

### 6.6 Trust-but-verify on sub-agent output

If you dispatch any sub-agent (Phase 4 Gate 1 may dispatch auditor agent):
- Don't trust the sub-agent's success report
- Read the actual file written
- Run any claimed mechanical verifications yourself
- Then advance state

---

## 7. Execution mode

Two options for Tasks 1-30:

### Option A — Subagent-driven (recommended)

Invoke `superpowers:subagent-driven-development`. Each task → fresh subagent. Review between tasks. Catches integration bugs early.

### Option B — Inline execution

Invoke `superpowers:executing-plans`. Walk tasks inline with Phase-boundary checkpoints.

**If founder hasn't specified at session start**: ask ONCE — "Subagent-driven (recommended) or inline execution?" — then proceed without re-asking.

---

## 8. Communication protocol

### 8.1 During execution

- Use **TodoWrite** to track task progress (mark `in_progress` before each task, `completed` after).
- **At phase boundaries**: report briefly to founder (3-5 lines). Format: *"Phase N done. M tasks, K files created. All tests pass. Moving to Phase N+1."*
- **Mid-phase**: silent execution. Don't narrate every commit.

### 8.2 On completion

When MVP is complete (Tasks 1-30 done, all 3 dogfood gates handled, tag created, pushed):
- Write a single completion summary (≤ 30 lines):
  - Final HEAD commit + tag
  - Test count (all passing)
  - Gate 1 / Gate 2 outcomes
  - Anything noteworthy for founder
- **NOT** a full transcript — founder will read the git log + plan completion record (Task 30).

### 8.3 On blocker

If you can't proceed:
- Surface IMMEDIATELY (don't bury in trying-stuff)
- Report: exact error + state.yaml current state + what you tried + what you need
- Do **NOT** auto-retry the same failing operation > 2 times
- Do **NOT** work around blockers by going off-plan

---

## 9. Acceptance criteria — when you're "done"

Mechanical checks (run before declaring done):

```bash
cd ~/Desktop/Arc\ Studio/arcgentic

# Check 1: all 30 tasks committed
git log --oneline f58526e..HEAD | wc -l  # expect ~25+ commits (some tasks share commits)

# Check 2: all tests pass
TOTAL=0; FAIL=0
for f in $(find scripts tests -name '*.test.sh'); do
  bash "$f" || FAIL=$((FAIL+1))
  TOTAL=$((TOTAL+1))
done
echo "$TOTAL test files, $FAIL failed"  # expect "10 test files, 0 failed"

# Check 3: plugin.json version bumped
grep '"version"' plugin.json  # expect "0.1.0-alpha.2"

# Check 4: tag created
git tag -l 'v0.1.0-alpha.2'  # expect "v0.1.0-alpha.2"

# Check 5: dogfood gates documented
test -f tests/dogfood/replay-r10-l3-llm/RESULT.md
test -f tests/dogfood/gate-2-live-run/RESULT.md
test -f tests/dogfood/gate-3-cross-project/PROTOCOL.md
echo "all dogfood files present: $?"  # expect 0

# Check 6: pushed to origin
git log origin/main..HEAD  # expect empty (everything pushed)
```

When all 6 checks pass: report completion to founder.

If Gate 1 (replay) fails: surface; founder decides whether to iterate or accept.
If Gate 2 (live run) fails: surface; this is more serious — likely a plugin bug, not just discrepancy.

---

## 10. Hard NOs (do not under any circumstances)

| # | Rule | Why |
|---|---|---|
| 1 | Do NOT cd into / commit to / push to Moirai repo | arcgentic + Moirai are separate; cross-contamination breaks discipline |
| 2 | Do NOT change plan scope without founder approval | Plan is the contract |
| 3 | Do NOT add paid-API integrations | § 6.1 cost discipline |
| 4 | Do NOT auto-create v0.2 work | v0.2 is a future plan; stop after Tasks 1-30 |
| 5 | Do NOT skip writing tests | TDD discipline |
| 6 | Do NOT force-push to main | Destructive; never without explicit permission |
| 7 | Do NOT add files outside `~/Desktop/Arc Studio/arcgentic/` | Stay in your workspace |
| 8 | Do NOT install dependencies that aren't in plan prereqs | (Bash + Python3 + PyYAML + jsonschema only) |
| 9 | Do NOT poll founder availability | They check in; don't interrupt |
| 10 | Do NOT use `--no-verify` / `--no-gpg-sign` on commits | Honor hooks; if a hook fails, fix the cause |

---

## 11. Environment

| Component | Required version | Notes |
|---|---|---|
| Bash | ≥ 4 | macOS default is /bin/bash 3 — use `#!/usr/bin/env bash` everywhere |
| Python 3 | ≥ 3.8 | Embedded inline in Bash scripts via heredocs |
| Python packages | PyYAML + jsonschema | `python3 -m pip install --user PyYAML jsonschema` |
| Git | any recent | `git remote -v` should show `origin → Arch1eSUN/Arcgentic.git` |
| gh CLI | any recent | Authenticated for Arch1eSUN/Arcgentic — used in Phase 4 for verifying repo state |
| Claude Code | ≥ 1.0 | This is the host runtime |
| `superpowers` plugin | required | For `superpowers:subagent-driven-development` / `superpowers:executing-plans` / `superpowers:verification-before-completion` / `superpowers:requesting-code-review` |
| `plugin-dev` plugin | recommended | For `plugin-dev:skill-reviewer` + `plugin-dev:plugin-validator` quality gates; if missing, manually verify against Anthropic skill conventions |

**Verify environment before Task 1**:

```bash
bash --version | head -1                                    # expect "GNU bash, version 4.x" or higher
python3 --version                                           # expect "Python 3.8" or higher
python3 -c "import yaml, jsonschema; print('ok')"           # expect "ok"
git remote -v                                               # expect "origin git@github.com:Arch1eSUN/Arcgentic.git"
gh auth status                                              # expect "Logged in to github.com"
```

If anything fails: install missing piece, re-verify, then proceed.

---

## 12. Founder communication

| Detail | Value |
|---|---|
| Founder name | archiesun |
| Founder preferred chat language | 中文 (Chinese); code / git / files in English |
| Founder reachability | Periodic chat check-ins; do NOT poll their availability |
| Founder is working on | Moirai project (parallel session — they're separately busy with `R10-L3-codex-cliproxy-vendor`) |

**Founder-friendly status reports** are 3-5 lines, in Chinese, factual:
> "Phase 1 完成。11 个 task，14 个新文件，46 个 test 全过。下一步 Phase 2 (5 个 skill + 12 个 reference doc)。"

NOT:
> "I successfully completed Phase 1 with great care, ensuring all..."

---

## 13. Origin (context — read once, then forget)

You are inheriting work from a previous Claude Opus 4.7 audit-only **planning instance** that:
1. Was asked by founder to encapsulate Moirai's 30+ rounds of engineering discipline as a generic Claude Code plugin
2. Iterated with founder through 5 design decisions (D1 name=`arcgentic` / D2 YAML state / D3 hard gates + optional hooks / D4 platform-neutral agents / D5 minimal viable four-pack first)
3. Wrote the plugin scaffold (commit 70b6773)
4. Wrote the 4580-line MVP plan via `superpowers:writing-plans` (commit f58526e)
5. Set up GitHub remote + pushed + updated description + topics (commit d7da73c)
6. Wrote this handoff (your current `CLAUDE.md`)

That planning instance is **closed**. You are a **fresh dev session** with no inherited conversation context. The plan is the contract — execute it.

The Moirai project (parent inspiration) lives at `~/Desktop/Arc Studio/Moirai/`. You may **read** files there if it helps understand Moirai patterns being distilled (e.g. an existing verdict format for Gate 1 replay). You may **NOT write** to Moirai.

---

## 14. First action when this session starts

```
1. Read this CLAUDE.md fully (you're doing it now)
2. Run environment verification (§ 11)
3. Read plugin.json + README.md
4. Read docs/plans/2026-05-12-arcgentic-mvp-plan.md (full plan)
5. Ask founder: "执行模式: subagent-driven (推荐) 还是 inline?"
6. After founder answers: invoke the corresponding superpowers skill + begin Task 1
```

---

## 15. End-state

When you're done, this CLAUDE.md will be replaced by a project-mandate file (similar to Moirai's CLAUDE.md § 8 mandates, but for arcgentic-specific lessons accumulated during MVP execution).

For now: this is your orientation. Read it, internalize it, then execute.

Good luck. The plan is comprehensive — trust it.
