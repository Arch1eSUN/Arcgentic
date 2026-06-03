# R3-v1-prepublish-fix Developer Self-Audit Handoff

## § 1. Identity Boundary

Role: developer self-audit only.

This document is not an external audit verdict, does not close R3, and does not
tag or publish v1.0.0. External audit owns the PASS / NEEDS_FIX /
AUDIT_INCOMPLETE verdict.

## § 2. Scope Implemented

- Generated execute-round self-audit facts now avoid mutable current-state
  assertions and moving `HEAD` equality checks.
- Generated self-audit facts now use stable artifact existence and fixed commit
  anchor rows when full commit SHAs are available.
- Regression tests cover re-running generated self-audit facts after synthetic
  `HEAD` advancement and synthetic `awaiting_audit -> audit_in_progress` state
  advancement.
- `codify-lesson` now extracts P2/P3 occurrences only from structured findings
  tables with a `Priority` column and a summary/finding/description column.
- R2-style forward-debt prose and author-note prose no longer produce noisy
  lessons such as `future-fact-audit-state-both`.
- Real repeated structured finding rows still promote stable lesson cards.
- `docs/tech-debt.md` marks both R2 prepublish debts resolved while preserving
  v0.3 forward-debts.

## § 3. Out-of-Scope Boundaries Honored

- Did not write an external audit verdict.
- Did not tag or publish v1.0.0.
- Did not expand into `ER-RETRY`, `ER-AUDIT-FACTS-RICH`, or `ER-STATE-ROW`.
- Did not touch Moirai.
- Did not call paid APIs, start background services, or install third-party
  plugins.

## § 4. Developer Commit Chain

The final developer commit chain is recorded in `.agentic-rounds/state.yaml`
under `current_round.dev_commits`.

Known commits before this final self-audit commit:

- `caf344e` — `fix(execute-round): stabilize self-audit facts`
- `81454cc` — `fix(codify-lesson): extract structured findings only`

## § 5. Implementation Notes

The execute-round generator cannot know the commit SHA of its own future
self-audit commit before running audit-check. Therefore the generator avoids
future-self-reference and only emits facts that can pass at generation time:
smoke, artifact existence, and fixed phase commit anchors when known.

The R3 round-specific self-audit below uses state-recorded anchors after the
final commit is known. These facts are intended to remain valid after the
auditor moves state to `audit_in_progress`.

## § 6. Residual Risk

`ER-AUDIT-FACTS-RICH` remains active by design: the generator is now stable, but
it still does not generate a rich 25-40 fact table from changed files and commit
chain semantics.

## § 7. Mechanical audit facts

20 facts verified by this developer self-audit. Auditor should re-run these
facts independently.

| # | Command | Expected | Comment |
|---|---|---|---|
| 1 | `git rev-parse --show-toplevel` | `/Users/archiesun/Desktop/Arc Studio/arcgentic` | repo root |
| 2 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && bash scripts/state/validate-schema.sh .agentic-rounds/state.yaml` | `valid: .agentic-rounds/state.yaml` | state schema valid |
| 3 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -c "import yaml; s=yaml.safe_load(open('.agentic-rounds/state.yaml')); h=[x['state'] for x in s['current_round']['state_history']]; print('dev_in_progress' in h and 'awaiting_audit' in h)"` | `True` | stable state-history check |
| 4 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -c "import subprocess,yaml; s=yaml.safe_load(open('.agentic-rounds/state.yaml')); cs=s['current_round']['dev_commits']; ok=len(cs)==3 and all(subprocess.run(['git','cat-file','-e', c+'^{commit}']).returncode==0 for c in cs); print(ok)"` | `True` | dev commit chain resolves |
| 5 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -c "from pathlib import Path; import yaml; s=yaml.safe_load(open('.agentic-rounds/state.yaml')); print(Path(s['current_round']['self_audit_doc']['path']).exists())"` | `True` | self-audit artifact exists |
| 6 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -c "import subprocess,yaml; s=yaml.safe_load(open('.agentic-rounds/state.yaml')); c=s['current_round']['self_audit_doc']['commit']; print(subprocess.run(['git','cat-file','-e', c+'^{commit}']).returncode == 0)"` | `True` | self-audit commit resolves |
| 7 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -c "import subprocess,yaml; s=yaml.safe_load(open('.agentic-rounds/state.yaml')); d=s['current_round']['self_audit_doc']; print(subprocess.run(['git','cat-file','-e', d['commit']+':'+d['path']]).returncode == 0)"` | `True` | self-audit path exists at fixed commit |
| 8 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && ! rg -n "current_round.*state.*awaiting_audit\|git rev-parse HEAD.*self_audit_doc.commit" toolkit/src/arcgentic/skills_impl/execute_round.py && echo ok` | `ok` | generated facts avoid current-state and moving-HEAD assertions |
| 9 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && pytest tests/unit/skills_impl/test_execute_round.py::test_self_audit_facts_survive_head_advance --tb=short -q \| tail -1 \| sed -E 's/ in [0-9.]+s//'` | `1 passed` | synthetic HEAD advance coverage |
| 10 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && pytest tests/unit/skills_impl/test_execute_round.py::test_self_audit_facts_survive_audit_state_advance --tb=short -q \| tail -1 \| sed -E 's/ in [0-9.]+s//'` | `1 passed` | synthetic audit state advance coverage |
| 11 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && pytest tests/unit/skills_impl/test_codify_lesson.py::test_codify_lesson_ignores_r2_style_forward_debt_prose --tb=short -q \| tail -1 \| sed -E 's/ in [0-9.]+s//'` | `1 passed` | R2-style noisy prose ignored |
| 12 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && pytest tests/unit/skills_impl/test_codify_lesson.py::test_codify_lesson_promotes_three_occurrences --tb=short -q \| tail -1 \| sed -E 's/ in [0-9.]+s//'` | `1 passed` | real structured finding promotion preserved |
| 13 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && pytest --tb=short -q \| tail -1 \| sed -E 's/ in [0-9.]+s//'` | `322 passed` | full pytest suite |
| 14 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && mypy --strict src/ tests/ \| tail -1` | `Success: no issues found in 67 source files` | mypy strict |
| 15 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic/toolkit" && ruff check . \| tail -1` | `All checks passed!` | ruff |
| 16 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic` | `Plugin validation passed: /Users/archiesun/Desktop/Arc Studio/arcgentic` | Codex plugin manifest |
| 17 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -m arcgentic.cli v1-release-readiness --repo-root . \| python3 -c "import json,sys; print(json.load(sys.stdin)['ok'])"` | `True` | v1 release readiness |
| 18 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && python3 -c "from pathlib import Path; text=Path('docs/tech-debt.md').read_text(); active=text.split('## Resolved')[0]; resolved=text.split('## Resolved')[1]; print('R2-SELF-AUDIT-MUTABLE-FACTS' not in active and 'R2-CODIFY-LESSON-PRECISION' not in active and 'R2-SELF-AUDIT-MUTABLE-FACTS' in resolved and 'R2-CODIFY-LESSON-PRECISION' in resolved)"` | `True` | R2 debts resolved |
| 19 | `bash -lc 'tag=$(git tag -l v1.0.0); if [ -z "$tag" ]; then echo NONE; else echo "$tag"; fi'` | `NONE` | no v1.0.0 tag |
| 20 | `cd "/Users/archiesun/Desktop/Arc Studio/arcgentic" && bash -lc 'git diff --name-only ab7018204c2df6578a7f8f3abec7c43165f12d21..HEAD \| rg "Moirai" \| wc -l \| tr -d " "'` | `0` | no Moirai path modified |

## § 8. Developer Self-Audit Result

READY_FOR_EXTERNAL_AUDIT.

This developer session stops at `awaiting_audit`. External auditor must verify
the fact table and write the external verdict.
