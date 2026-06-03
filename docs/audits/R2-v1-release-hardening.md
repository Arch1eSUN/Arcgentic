# R2-v1-release-hardening — External Audit Verdict

**Outcome:** PASS
**Audited dev commits:** `fa2086db206ace75a796efb9657eb613b0bb17b5` `cb8016661ad21c130a4c972f7198478f2b245395` `90a2f16f7a88d56dea311ecc7ad42f34caf71402` `701d5de314cb8702b539ee9a28807eaf3bffd174`
**Audited audit commit:** `28facb74d7613f6c09d2db336471b97efd9826df`
**Auditor:** Codex external auditor
**Audited at:** 2026-06-03

## 1. Executive summary

PASS. The R2 release-hardening seams are implemented and independently verified: project-level `multi-session` is inherited, orchestrator dispatch order exists, close-round has state/anchor/closed-transition guards, role-specific prompts work, verdict completeness distinguishes all three structured outcomes, release-readiness passes, no Moirai path was touched, and no `v1.0.0` tag exists.

## 2. Findings

| Id | Priority | Summary | Evidence | Expected | Actual | Recommended fix | Verification |
|---|---|---|---|---|---|---|---|
| D-R2-v1-release-hardening-1 | P2 | Self-audit facts #3 and #19 are historical current-state/current-HEAD facts, not stable re-audit facts. | `docs/audits/R2-v1-release-hardening-self-audit.md` fact #3 expects `awaiting_audit`; fact #19 expects current `HEAD` to equal the dev self-audit commit. Both become stale after valid audit/closeout commits. | Self-audit facts intended for external rerun should remain stable after `awaiting_audit -> audit_in_progress` and after audit verdict commits, or explicitly verify state_history/fixed dev anchors. | Current state has advanced past `awaiting_audit`, and current `HEAD` can advance beyond the dev commit while the state self-audit anchor remains valid. | In a future cleanup, change developer self-audit state facts to verify state_history or self_audit_doc artifact instead of current mutable state/HEAD. | Fact rows 3-4 document the raw failure and the stable replacement check. |

## 3. Lesson codification result

No applicable mandate promotion. This is the first observed instance in this audit lane of a self-audit fact becoming stale after a valid audit transition.

## 4. Mistake-pattern checks

| Pattern | Applied? | Result |
|---|---|---|
| Fix-example-vs-contract | No | Not a fix-round. |
| Sibling-doc-sweep | Yes | PASS. Release-hardening surfaces were updated across README, README.zh-CN, manifests, and role skills; release-readiness returns `ok: true`. |
| Doc-vs-impl re-grep | Yes | PASS. Required seams have implementation/test evidence in fact rows 5-19. |

## 5. Reference scan compliance

| # | Which | Why | What part | NOT used |
|---|---|---|---|---|
| 1 | `docs/audits/R1-v1-openspec-marketplace.md` | Carries the prior successful verdict and P2 role-selector debt | R1 P2 prompt-role finding and fact-table shape | No R1 verdict edits by developer |
| 2 | `docs/tech-debt.md` | Carries closeout and prompt-role debts | release hardening debt targets | No unrelated debt rewrite |
| 3 | `skills/using-arcgentic/SKILL.md` | Current role model | project-level mode and role workflow language | No mode re-questioning |
| 4 | `skills/orchestrate-round/SKILL.md` | Orchestrator behavior | dispatch/closeout loop | No real closeout execution |
| 5 | `schema/state.schema.json` | State interface | project.session_mode, current_round, audit_verdict, last_passed_round | No closed R1 history rewrite |

## 6. Cross-mandate compliance

| Mandate | Honored? | Evidence |
|---|---|---|
| Auditor only | YES | This session wrote only the external verdict and state verdict summary; no implementation code was changed. |
| Multi-session fixed | YES | Fact row 5 returns `multi-session,False`. |
| No real closeout | YES | State transitions only to `passed`; no `closed` transition was executed. |
| No Moirai writes | YES | Fact row 18 returns `0`. |
| No v1.0.0 tag | YES | Fact row 17 returns `NONE`. |
| P2/P3 do not trigger NEEDS_FIX | YES | Verdict is PASS with 0 P0/P1 and 1 P2. |

## 7. Fact table

| # | Command | Expected | Comment | Actual |
|---|---|---|---|---|
| 1 | `git rev-parse 701d5de314cb8702b539ee9a28807eaf3bffd174` | `701d5de314cb8702b539ee9a28807eaf3bffd174` | audited dev HEAD resolves | `701d5de314cb8702b539ee9a28807eaf3bffd174` |
| 2 | `bash scripts/state/validate-schema.sh .agentic-rounds/state.yaml` | `valid: .agentic-rounds/state.yaml` | state schema valid | `valid: .agentic-rounds/state.yaml` |
| 3 | `cd toolkit && python3 -m arcgentic.cli audit-check ../docs/audits/R2-v1-release-hardening-self-audit.md --strict-extended \| head -1 \| python3 -c "import sys; print(sys.stdin.read().strip().replace(\"PASS\",\"OK\").replace(chr(124),\"/\"))"` | `17/19 OK, 2 FAIL, 0 SKIP / AC-1: 0 violation(s) / AC-3: 0 violation(s)` | raw self-audit §7 rerun after audit commits, transformed to avoid verdict AC-1 ambiguity | `17/19 OK, 2 FAIL, 0 SKIP / AC-1: 0 violation(s) / AC-3: 0 violation(s)` |
| 4 | `bash -lc 'python3 -c "import yaml; s=yaml.safe_load(open(\".agentic-rounds/state.yaml\")); h=[x[\"state\"] for x in s[\"current_round\"][\"state_history\"]]; print(str(\"awaiting_audit\" in h and \"audit_in_progress\" in h))"'` | `True` | stable replacement for historical developer stop-state fact | `True` |
| 5 | `cd toolkit && python3 -c "from arcgentic.session_mode import should_request_session_mode; import yaml; s=yaml.safe_load(open('../.agentic-rounds/state.yaml')); print(s['project']['session_mode']['mode']+','+str(should_request_session_mode(s, 'R2-v1-release-hardening')))"` | `multi-session,False` | project-level mode inherited, no per-round question | `multi-session,False` |
| 6 | `cd toolkit && python3 -m arcgentic.cli orchestrator-dispatch --round R2-v1-release-hardening --handoff ../docs/superpowers/plans/2026-06-03-R2-v1-release-hardening-handoff.md --mode multi-session \| python3 -c "import json,sys; d=json.load(sys.stdin); print(' -> '.join(step['role'] for step in d['steps'])+';'+d['steps'][0]['stop_condition'])"` | `developer -> auditor -> closeout;implementation complete, self-audit written, state = awaiting_audit` | orchestrator dispatch order exists | `developer -> auditor -> closeout;implementation complete, self-audit written, state = awaiting_audit` |
| 7 | `cd toolkit && python3 -c "import subprocess; base=['python3','-m','arcgentic.cli','session-mode','prompt','--round','R2-v1-release-hardening','--handoff','../docs/superpowers/plans/2026-06-03-R2-v1-release-hardening-handoff.md','--mode','multi-session']; print(';'.join(subprocess.check_output([*base,'--role',role], text=True).splitlines()[0] for role in ['developer','auditor','closeout']))"` | `You are the arcgentic developer only for round R2-v1-release-hardening.;You are the arcgentic auditor only for round R2-v1-release-hardening.;You are the arcgentic closeout only session for round R2-v1-release-hardening.` | role-specific prompts selectable | `You are the arcgentic developer only for round R2-v1-release-hardening.;You are the arcgentic auditor only for round R2-v1-release-hardening.;You are the arcgentic closeout only session for round R2-v1-release-hardening.` |
| 8 | `cd toolkit && pytest tests/unit/test_close_round.py --tb=short -q >/tmp/arcgentic-r2-close-tests.out && grep -o '[0-9][0-9]* passed' /tmp/arcgentic-r2-close-tests.out \| tail -1 \| awk '{print $1}'` | `4` | close-round state guard, anchor guard, closed transition tests | `4` |
| 9 | `cd toolkit && pytest tests/unit/test_verdict_completeness.py --tb=short -q >/tmp/arcgentic-r2-verdict-tests.out && grep -o '[0-9][0-9]* passed' /tmp/arcgentic-r2-verdict-tests.out \| tail -1 \| awk '{print $1}'` | `4` | verdict completeness PASS/NEEDS_FIX/AUDIT_INCOMPLETE tests | `4` |
| 10 | `cd toolkit && pytest --tb=short -q >/tmp/arcgentic-r2-audit-pytest.out && grep -o '[0-9][0-9]* passed' /tmp/arcgentic-r2-audit-pytest.out \| tail -1 \| awk '{print $1}'` | `317` | full pytest suite | `317` |
| 11 | `cd toolkit && mypy --strict src/ tests/ \| tail -1` | `Success: no issues found in 67 source files` | mypy strict | `Success: no issues found in 67 source files` |
| 12 | `cd toolkit && ruff check . \| tail -1` | `All checks passed!` | ruff | `All checks passed!` |
| 13 | `bash -lc 'python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic'` | `Plugin validation passed: /Users/archiesun/Desktop/Arc Studio/arcgentic` | plugin validator | `Plugin validation passed: /Users/archiesun/Desktop/Arc Studio/arcgentic` |
| 14 | `cd toolkit && python3 -m arcgentic.cli v1-release-readiness --repo-root .. \| python3 -c "import json,sys; print(json.load(sys.stdin)['ok'])"` | `True` | v1 release readiness | `True` |
| 15 | `bash -lc 'git diff --name-only a38e6780aa4d7ba358ce869a7e0e2558c306c470..HEAD \| rg "Moirai" \| wc -l \| tr -d " "'` | `0` | no Moirai path modified | `0` |
| 16 | `bash -lc 'tag=$(git tag -l v1.0.0); if [ -z "$tag" ]; then echo NONE; else echo "$tag"; fi'` | `NONE` | no v1.0.0 tag | `NONE` |
| 17 | `bash -lc 'python3 -c "import yaml; s=yaml.safe_load(open(\".agentic-rounds/state.yaml\")); print(\",\".join(c[:7] for c in s[\"current_round\"][\"dev_commits\"]))"'` | `fa2086d,cb80166,90a2f16,701d5de` | dev commit chain recorded | `fa2086d,cb80166,90a2f16,701d5de` |
| 18 | `bash -lc 'test "701d5de314cb8702b539ee9a28807eaf3bffd174" = "$(python3 -c "import yaml;print(yaml.safe_load(open(\".agentic-rounds/state.yaml\"))[\"current_round\"][\"self_audit_doc\"][\"commit\"])" )" && echo true'` | `true` | self-audit commit anchored to audited dev HEAD | `true` |
| 19 | `bash -lc 'python3 -c "from pathlib import Path; text=chr(10).join(Path(p).read_text() for p in [\"README.md\",\"README.zh-CN.md\",\"plugin.json\",\".codex-plugin/plugin.json\",\"openclaw.plugin.json\"]); print(all(s in text for s in [\"close-round\",\"project-level session mode\",\"0.2.2-alpha.3\"]))"'` | `True` | docs/manifests aligned | `True` |

**Sub-total:** 19/19 facts PASS.

## 8. Forward-debt observations

- D-R2-v1-release-hardening-1 (P2): make future self-audit state/HEAD facts stable across audit and closeout transitions by checking `state_history` and fixed dev anchors instead of current mutable state/HEAD.

## 9. Author's note

The release-hardening work is cohesive and matches the R2 handoff. The one P2 is about audit fact durability across state and HEAD transitions, not product behavior. No P0/P1 blockers remain.

Outcome: PASS. Fact table 19/19. P0/P1/P2/P3 finding count: 0/0/1/0.
