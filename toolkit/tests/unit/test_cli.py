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
