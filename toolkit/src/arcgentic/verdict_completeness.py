"""Validate external audit verdict outcome and finding completeness."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VerdictCompletenessResult:
    ok: bool
    outcome: str
    issues: tuple[str, ...]


_OUTCOMES = ("PASS", "NEEDS_FIX", "AUDIT_INCOMPLETE")
_REQUIRED_FINDING_COLUMNS = (
    "id",
    "priority",
    "summary",
    "evidence",
    "expected",
    "actual",
    "recommended fix",
    "verification",
)


def validate_verdict_completeness(markdown: str) -> VerdictCompletenessResult:
    """Validate that verdict outcomes and findings are mechanically actionable."""

    outcome = _parse_outcome(markdown)
    issues: list[str] = []
    if outcome not in _OUTCOMES:
        issues.append("verdict outcome must be PASS, NEEDS_FIX, or AUDIT_INCOMPLETE")
        outcome = outcome or "UNKNOWN"

    findings = _parse_findings(markdown)
    if outcome in ("NEEDS_FIX", "AUDIT_INCOMPLETE") and not findings:
        issues.append(f"{outcome} requires at least one structured finding")
    if findings:
        columns = findings[0]
        missing = [column for column in _REQUIRED_FINDING_COLUMNS if column not in columns]
        if missing:
            issues.append("missing required finding columns: " + ", ".join(missing))
        for row in findings[1:]:
            if len(row) < len(columns) or any(not cell for cell in row[: len(columns)]):
                issues.append("finding rows must fill every required field")
                break
    if outcome == "PASS" and findings:
        blocker_rows = [row for row in findings[1:] if len(row) > 1 and row[1] in ("P0", "P1")]
        if blocker_rows:
            issues.append("PASS verdict cannot contain P0/P1 findings")

    return VerdictCompletenessResult(ok=not issues, outcome=outcome, issues=tuple(issues))


def _parse_outcome(markdown: str) -> str:
    match = re.search(
        r"(?:\*\*)?\bOutcome\s*:\s*(?:\*\*)?\s*(PASS|NEEDS_FIX|AUDIT_INCOMPLETE)\b",
        markdown,
    )
    return match.group(1) if match else ""


def _parse_findings(markdown: str) -> list[list[str]]:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells and "id" in cells and "priority" in cells:
            rows = [cells]
            for row in lines[index + 2 :]:
                parsed = _cells(row)
                if not parsed:
                    break
                rows.append(parsed)
            return rows
    return []


def _cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
    if all(set(cell) <= {"-", ":"} for cell in cells):
        return []
    return cells
