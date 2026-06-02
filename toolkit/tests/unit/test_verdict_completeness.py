from __future__ import annotations

from arcgentic.verdict_completeness import validate_verdict_completeness


def test_rejects_bare_needs_fix_without_structured_findings() -> None:
    result = validate_verdict_completeness("Outcome: NEEDS_FIX\n")

    assert result.ok is False
    assert "NEEDS_FIX requires at least one structured finding" in result.issues


def test_accepts_pass_without_findings() -> None:
    result = validate_verdict_completeness("Outcome: PASS\n")

    assert result.ok is True


def test_accepts_audit_incomplete_with_structured_reason() -> None:
    result = validate_verdict_completeness(
        """Outcome: AUDIT_INCOMPLETE

| Id | Priority | Summary | Evidence | Expected | Actual | Recommended fix | Verification |
|---|---|---|---|---|---|---|---|
| A-1 | P1 | State | `state.yaml` | awaiting | planning | rerun | pickup ok |
"""
    )

    assert result.ok is True
    assert result.outcome == "AUDIT_INCOMPLETE"


def test_rejects_finding_missing_required_columns() -> None:
    result = validate_verdict_completeness(
        """Outcome: NEEDS_FIX

| Id | Priority | Summary |
|---|---|---|
| F-1 | P1 | Missing evidence |
"""
    )

    assert result.ok is False
    assert "missing required finding columns" in result.issues[0]
