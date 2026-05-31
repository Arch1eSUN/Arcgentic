"""Validators for the portable source-rule contract.

The source-rule contract is the Moirai-derived planning/dev/audit discipline captured in
docs/plans/2026-05-30-arcgentic-source-rule-alignment.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_REFERENCE_USE_MODES = {
    "direct use",
    "rebuild",
    "enhance",
    "strengthen",
    "adapt",
    "reference-only",
}


@dataclass(frozen=True)
class HandoffValidationResult:
    """Result of validating a planning handoff against the source-rule contract."""

    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        if self.ok:
            return "source-rule handoff validation PASS"
        lines = ["source-rule handoff validation FAIL"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def validate_handoff_contract(markdown: str) -> HandoffValidationResult:
    """Validate the required semantic slots of a planning handoff.

    This validator intentionally checks the source-rule contract, not a specific template
    size. A 10/12/18-section handoff can pass if it contains the required semantics.
    """
    lower = markdown.lower()
    errors: list[str] = []

    _require_contains(lower, "allowed scope", "missing allowed scope", errors)
    if "forbidden scope" not in lower and "anti-scope" not in lower:
        errors.append("missing forbidden scope")

    _require_reference_table(markdown, errors)

    _require_contains(lower, "tooling plan", "missing tooling plan", errors)
    _require_contains(lower, "implementation task", "missing implementation tasks", errors)
    _require_contains(lower, "required test", "missing required tests", errors)
    _require_contains(lower, "required audit fact", "missing required audit facts", errors)
    _require_contains(lower, "stop condition", "missing stop condition", errors)
    _require_contains(lower, "devsession message", "missing devsession message", errors)

    if "read:" not in lower or "start round:" not in lower or "stop after:" not in lower:
        errors.append("devsession message must include Read, Start round, and Stop after fields")

    return HandoffValidationResult(errors=errors)


def validate_handoff_file(path: Path) -> HandoffValidationResult:
    """Read and validate a handoff file."""
    return validate_handoff_contract(path.read_text(encoding="utf-8"))


def _require_contains(haystack: str, needle: str, error: str, errors: list[str]) -> None:
    if needle not in haystack:
        errors.append(error)


def _require_reference_table(markdown: str, errors: list[str]) -> None:
    table = _first_reference_table(markdown)
    if table is None:
        errors.append("missing reference table")
        return

    headers, rows = table
    normalized_headers = [_normalize_cell(h) for h in headers]
    if "use mode" not in normalized_headers:
        errors.append("reference table must include a Use mode column")
        return

    mode_index = normalized_headers.index("use mode")
    for row in rows:
        if len(row) <= mode_index:
            errors.append("reference table row missing Use mode value")
            continue
        mode = _normalize_cell(row[mode_index])
        if mode not in _REFERENCE_USE_MODES:
            errors.append(f"invalid reference use mode: {row[mode_index].strip()}")


def _first_reference_table(markdown: str) -> tuple[list[str], list[list[str]]] | None:
    lines = markdown.splitlines()
    for idx, line in enumerate(lines):
        if not _is_table_row(line):
            continue
        headers = _split_table_row(line)
        if "reference" not in [_normalize_cell(h) for h in headers]:
            continue
        if idx + 1 >= len(lines) or not _is_separator_row(lines[idx + 1]):
            continue
        rows: list[list[str]] = []
        for row_line in lines[idx + 2 :]:
            if not _is_table_row(row_line):
                break
            rows.append(_split_table_row(row_line))
        return headers, rows
    return None


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_row(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(set(cell.strip()) <= {"-", ":"} for cell in cells)


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _normalize_cell(cell: str) -> str:
    return " ".join(cell.strip().lower().split())
