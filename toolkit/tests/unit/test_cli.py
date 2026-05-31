"""Tests for arcgentic.cli — the CLI entry point.

TDD: this file is written BEFORE cli.py exists.
Run order:
  1. pytest tests/unit/test_cli.py  → FAIL (ImportError)
  2. create cli.py
  3. pytest tests/unit/test_cli.py  → PASS
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from arcgentic.cli import main
from arcgentic.skills_impl.plan_round import RunResult

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_VALID_SHA = "a" * 40


def _make_mock_result(
    exit_code: int = 0,
    section_count: int = 18,
    loc: int = 250,
    handoff_path: Path | None = None,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> RunResult:
    """Build a mock RunResult with the given values."""
    return RunResult(
        handoff_path=handoff_path or Path("docs/superpowers/plans/2026-05-13-R1.0-handoff.md"),
        section_count=section_count,
        loc=loc,
        warnings=warnings or [],
        exit_code=exit_code,
        error=error,
    )


# ---------------------------------------------------------------------------
# 1. plan-round-impl dispatch → calls plan_round.run, returns exit_code
# ---------------------------------------------------------------------------


def test_plan_round_impl_dispatch() -> None:
    """main([plan-round-impl, ...]) calls plan_round.run and returns its exit_code."""
    with patch("arcgentic.skills_impl.plan_round.run") as mock_run:
        mock_run.return_value = _make_mock_result(exit_code=0)
        exit_code = main(
            [
                "plan-round-impl",
                "--round=R1.0",
                "--type=substrate-touching",
                f"--anchor={_VALID_SHA}",
            ]
        )
        assert exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["round_name"] == "R1.0"
        assert call_kwargs["round_type"] == "substrate-touching"
        assert call_kwargs["prior_round_anchor"] == _VALID_SHA


# ---------------------------------------------------------------------------
# 2. plan-round-impl with --scope passes scope to run
# ---------------------------------------------------------------------------


def test_plan_round_impl_with_scope() -> None:
    """--scope argument is passed to plan_round.run as scope_description."""
    with patch("arcgentic.skills_impl.plan_round.run") as mock_run:
        mock_run.return_value = _make_mock_result(exit_code=0)
        exit_code = main(
            [
                "plan-round-impl",
                "--round=R2.0",
                "--type=fix-round",
                f"--anchor={_VALID_SHA}",
                "--scope=Add auth module to the API layer.",
            ]
        )
        assert exit_code == 0
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["scope_description"] == "Add auth module to the API layer."


# ---------------------------------------------------------------------------
# 3. plan-round-impl propagates non-zero exit_code from plan_round.run
# ---------------------------------------------------------------------------


def test_plan_round_impl_propagates_failure_exit_code() -> None:
    """When plan_round.run returns exit_code=1, main returns 1."""
    with patch("arcgentic.skills_impl.plan_round.run") as mock_run:
        mock_run.return_value = _make_mock_result(
            exit_code=1,
            section_count=0,
            loc=0,
            handoff_path=None,
            error="planner dispatch failed",
        )
        exit_code = main(
            [
                "plan-round-impl",
                "--round=R1.0",
                "--type=substrate-touching",
                f"--anchor={_VALID_SHA}",
            ]
        )
        assert exit_code == 1


# ---------------------------------------------------------------------------
# 4. Missing --round: argparse error (exit code 2 from argparse)
# ---------------------------------------------------------------------------


def test_missing_round_arg() -> None:
    """Missing --round → argparse exits with SystemExit(2)."""
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "plan-round-impl",
                "--type=substrate-touching",
                f"--anchor={_VALID_SHA}",
            ]
        )
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# 5. Invalid --type: argparse choices error
# ---------------------------------------------------------------------------


def test_invalid_type_arg() -> None:
    """Invalid --type value → argparse exits with SystemExit(2)."""
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "plan-round-impl",
                "--round=R1.0",
                "--type=invalid-type-that-doesnt-exist",
                f"--anchor={_VALID_SHA}",
            ]
        )
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# 6. main([]) with no subcommand: prints help, returns 1
# ---------------------------------------------------------------------------


def test_no_subcommand_returns_1() -> None:
    """main([]) → no subcommand given → returns 1."""
    exit_code = main([])
    assert exit_code == 1


# ---------------------------------------------------------------------------
# 7. plan-round-impl with short anchor: passes args, plan_round.run handles validation
# ---------------------------------------------------------------------------


def test_short_anchor_reaches_plan_round() -> None:
    """Short anchor passes through argparse (no argparse validation), reaches plan_round.run."""
    with patch("arcgentic.skills_impl.plan_round.run") as mock_run:
        # plan_round.run returns exit_code=2 (input validation error)
        mock_run.return_value = _make_mock_result(
            exit_code=2,
            section_count=0,
            loc=0,
            handoff_path=None,
            error="Invalid prior_round_anchor: 'short'. Must be a full 40-char hex SHA.",
        )
        exit_code = main(
            [
                "plan-round-impl",
                "--round=R1.0",
                "--type=substrate-touching",
                "--anchor=short",
            ]
        )
        assert exit_code == 2
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 8. Default scope_description is empty string when not provided
# ---------------------------------------------------------------------------


def test_default_scope_is_empty_string() -> None:
    """When --scope is not provided, scope_description defaults to ''."""
    with patch("arcgentic.skills_impl.plan_round.run") as mock_run:
        mock_run.return_value = _make_mock_result(exit_code=0)
        main(
            [
                "plan-round-impl",
                "--round=R1.0",
                "--type=entry-admin",
                f"--anchor={_VALID_SHA}",
            ]
        )
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["scope_description"] == ""


# ---------------------------------------------------------------------------
# 9. validate-handoff dispatch → returns 0 when source-rule contract passes
# ---------------------------------------------------------------------------


def test_validate_handoff_passes_for_valid_file(tmp_path: Path) -> None:
    """validate-handoff reads a markdown handoff and returns 0 when valid."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(
        """# R1.0 — Handoff

## 1. Scope
Allowed scope: validator only.
Forbidden scope: no runtime adapters.

## 2. References
| Reference | Use mode | Why relevant | Exact surfaces to inspect |
|---|---|---|---|
| example/repo | Rebuild | Similar state machine | `src/state.ts` |

## 3. Tooling Plan
Required skills: arcgentic:plan-round.
Considered but not used: Browser.
Forbidden tools: paid API calls.

## 4. Implementation tasks
Add validator.

## 5. Required tests
Run pytest.

## 6. Required audit facts
Use fixed commit range.

## 7. Stop condition
Stop after: commit + push + CI green + audit handoff + worktree clean.

## 8. Devsession message
Read: docs/plans/R1.0-handoff.md
Start round: R1.0
Allowed scope: validator only
Forbidden scope: no runtime adapters
Required references/tools: example/repo + pytest
Required verification: pytest
Stop after: commit + push + CI green + audit handoff + worktree clean
""",
        encoding="utf-8",
    )

    assert main(["validate-handoff", str(handoff)]) == 0


# ---------------------------------------------------------------------------
# 10. validate-handoff dispatch → returns 1 when source-rule contract fails
# ---------------------------------------------------------------------------


def test_validate_handoff_fails_for_invalid_file(tmp_path: Path) -> None:
    """validate-handoff returns 1 when required source-rule fields are missing."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text("# R1.0 — Handoff\n\n## 1. Scope\nOnly vibes.\n", encoding="utf-8")

    assert main(["validate-handoff", str(handoff)]) == 1


# ---------------------------------------------------------------------------
# 11. codify-lesson dispatch → promotes repeated audit patterns
# ---------------------------------------------------------------------------


def test_codify_lesson_dispatch(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for i in range(3):
        (audit_dir / f"R{i + 1}.md").write_text(
            "| F | P2 | audit handoff missing immutable evidence |\n",
            encoding="utf-8",
        )

    exit_code = main(
        [
            "codify-lesson",
            "--audit-dir",
            str(audit_dir),
            "--lessons-dir",
            str(tmp_path / "lessons"),
            "--amendments-dir",
            str(tmp_path / "mandates" / "amendments"),
        ]
    )

    assert exit_code == 0
    assert list((tmp_path / "lessons").glob("lesson-*-*.md"))


# ---------------------------------------------------------------------------
# 12. track-refs add → appends references/INDEX.md
# ---------------------------------------------------------------------------


def test_track_refs_add_dispatch(tmp_path: Path) -> None:
    repo = tmp_path / "references" / "sample"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# Sample reference\n", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    index = tmp_path / "references" / "INDEX.md"

    exit_code = main(
        [
            "track-refs",
            "add",
            str(repo),
            "--owner-repo",
            "owner/sample",
            "--round",
            "R1",
            "--index",
            str(index),
            "--usage-evidence",
            '{"pattern_only": true}',
        ]
    )

    assert exit_code == 0
    assert "owner/sample" in index.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 13. round-boundary-lesson-scan dispatch → supports dry-run
# ---------------------------------------------------------------------------


def test_round_boundary_lesson_scan_dispatch_dry_run(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for i in range(3):
        (audit_dir / f"R{i + 1}.md").write_text(
            "| F | P3 | source-rule handoff missing forbidden scope |\n",
            encoding="utf-8",
        )

    exit_code = main(
        [
            "round-boundary-lesson-scan",
            "--audit-dir",
            str(audit_dir),
            "--lessons-dir",
            str(tmp_path / "lessons"),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert not (tmp_path / "lessons").exists()


# ---------------------------------------------------------------------------
# 14. cross-session-handoff write/read dispatch
# ---------------------------------------------------------------------------


def test_cross_session_handoff_write_and_read_dispatch(tmp_path: Path) -> None:
    state = tmp_path / ".arcgentic" / "state.yaml"

    write_exit = main(
        [
            "cross-session-handoff",
            "write",
            "--state",
            str(state),
            "--session-id",
            "dev-session",
            "--updates",
            '{"current_round": "R4"}',
        ]
    )
    read_exit = main(["cross-session-handoff", "read", "--state", str(state)])

    assert write_exit == 0
    assert read_exit == 0
    assert "current_round: R4" in state.read_text(encoding="utf-8")
