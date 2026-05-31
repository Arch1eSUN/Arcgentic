"""Tests for source-rule contract validators.

These validators encode the portable Moirai-derived Planning / Dev / External Audit
discipline from docs/plans/2026-05-30-arcgentic-source-rule-alignment.md.
"""

from __future__ import annotations

from arcgentic.source_rules import validate_handoff_contract


def _valid_handoff() -> str:
    return """# R1.0 — Handoff

## 1. Scope

Allowed scope:
- Edit `src/foo.py`

Forbidden scope:
- Do not touch `src/bar.py`

## 2. References

| Reference | Use mode | Why relevant | Exact surfaces to inspect |
|---|---|---|---|
| example/repo | Rebuild | Similar state machine | `src/state.ts` |

## 3. Tooling Plan

Required skills:
- arcgentic:plan-round

Considered but not used:
- Browser — no UI surface

Forbidden tools:
- paid API calls

## 4. Implementation tasks

1. Add the validator.

## 5. Required tests

- `pytest toolkit/tests/unit/test_source_rules.py`

## 6. Required audit facts

- `git diff --name-only <parent>..<head>`

## 7. Stop condition

Stop after: commit + push + CI green + audit handoff + worktree clean.

## 8. Devsession message

```markdown
Read: docs/plans/R1.0-handoff.md
Start round: R1.0
Allowed scope: validator only
Forbidden scope: no runtime adapters
Required references/tools: example/repo + pytest
Required verification: pytest
Stop after: commit + push + CI green + audit handoff + worktree clean
```
"""


def test_valid_handoff_contract_passes() -> None:
    result = validate_handoff_contract(_valid_handoff())

    assert result.ok is True
    assert result.errors == []


def test_missing_reference_use_mode_fails() -> None:
    markdown = _valid_handoff().replace("| Reference | Use mode |", "| Reference | License |")

    result = validate_handoff_contract(markdown)

    assert result.ok is False
    assert "reference table must include a Use mode column" in result.errors


def test_invalid_reference_use_mode_fails() -> None:
    markdown = _valid_handoff().replace("| example/repo | Rebuild |", "| example/repo | Copy |")

    result = validate_handoff_contract(markdown)

    assert result.ok is False
    assert "invalid reference use mode: Copy" in result.errors


def test_missing_devsession_message_fails() -> None:
    markdown = _valid_handoff().replace("## 8. Devsession message", "## 8. Notes")

    result = validate_handoff_contract(markdown)

    assert result.ok is False
    assert "missing devsession message" in result.errors


def test_optional_test_session_is_not_required() -> None:
    result = validate_handoff_contract(_valid_handoff())

    assert "missing test session" not in result.errors
