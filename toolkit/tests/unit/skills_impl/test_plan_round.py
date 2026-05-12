"""Tests for arcgentic.skills_impl.plan_round.

TDD: this file is written BEFORE plan_round.py exists.
Run order:
  1. pytest tests/unit/skills_impl/test_plan_round.py  → FAIL (ImportError)
  2. create plan_round.py + skills_impl/__init__.py
  3. pytest tests/unit/skills_impl/test_plan_round.py  → PASS

Uses _StubAdapter (overrides InlineAdapter.dispatch_agent) to inject canned
planner outputs; no real `claude` subprocess is invoked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from arcgentic.adapters.base import AgentDispatchResult
from arcgentic.adapters.inline import InlineAdapter
from arcgentic.skills_impl.plan_round import (
    _ROUND_TYPE_TO_TEMPLATE_SIZE,
    PlanRoundError,
    RunResult,
    _build_planner_brief,
    _template_size_label,
    _validate_inputs,
    run,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_VALID_SHA = "a" * 40


def _make_sections(n: int) -> str:
    """Generate a minimal n-section markdown body."""
    lines = ["# Round Handoff\n"]
    for i in range(1, n + 1):
        lines.append(f"## {i}. Section {i}\n\nContent for section {i}.\n")
    lines.append(
        "*substrate-touching handoff written by planner agent (arcgentic v0.2.0-alpha.1).*"
    )
    return "\n".join(lines)


class _StubAdapter(InlineAdapter):
    """Test adapter — overrides dispatch_agent to return a canned output."""

    def __init__(
        self,
        canned_output: str,
        exit_code: int = 0,
        error: str | None = None,
    ) -> None:
        self._canned = canned_output
        self._exit_code = exit_code
        self._error = error

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: Literal["worktree"] | None = None,
    ) -> AgentDispatchResult:
        return AgentDispatchResult(
            output=self._canned,
            exit_code=self._exit_code,
            duration_ms=10,
            agent_type=agent_name,
            error=self._error,
        )


# ---------------------------------------------------------------------------
# 1. Input validation — invalid round_name
# ---------------------------------------------------------------------------


def test_invalid_round_name_returns_exit_code_2() -> None:
    """Malformed round_name → exit_code=2, error mentions round_name."""
    result = run(
        round_name="bad-name",
        round_type="fix-round",
        prior_round_anchor=_VALID_SHA,
        adapter=_StubAdapter(_make_sections(12)),
    )
    assert result.exit_code == 2
    assert result.error is not None
    assert "round_name" in result.error


# ---------------------------------------------------------------------------
# 2. Input validation — short SHA
# ---------------------------------------------------------------------------


def test_short_sha_returns_exit_code_2() -> None:
    """7-char SHA → exit_code=2, error mentions prior_round_anchor."""
    result = run(
        round_name="R1.0",
        round_type="fix-round",
        prior_round_anchor="abc1234",
        adapter=_StubAdapter(_make_sections(12)),
    )
    assert result.exit_code == 2
    assert result.error is not None
    assert "prior_round_anchor" in result.error


# ---------------------------------------------------------------------------
# 3. Input validation — bad round_type
# ---------------------------------------------------------------------------


def test_bad_round_type_returns_exit_code_2() -> None:
    """Unknown round_type → exit_code=2, error mentions round_type."""
    result = run(
        round_name="R1.0",
        round_type="foobar",
        prior_round_anchor=_VALID_SHA,
        adapter=_StubAdapter(_make_sections(18)),
    )
    assert result.exit_code == 2
    assert result.error is not None
    assert "round_type" in result.error


# ---------------------------------------------------------------------------
# 4. Round name R1.6.1 format
# ---------------------------------------------------------------------------


def test_round_name_three_component(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1.6.1 three-component format validates correctly."""
    monkeypatch.chdir(tmp_path)
    result = run(
        round_name="R1.6.1",
        round_type="fix-round",
        prior_round_anchor=_VALID_SHA,
        adapter=_StubAdapter(_make_sections(12)),
    )
    assert result.exit_code == 0, result.error


# ---------------------------------------------------------------------------
# 5. Round name R10-L3-aletheia format
# ---------------------------------------------------------------------------


def test_round_name_dash_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R10-L3-aletheia dash format validates correctly."""
    monkeypatch.chdir(tmp_path)
    result = run(
        round_name="R10-L3-aletheia",
        round_type="substrate-touching",
        prior_round_anchor=_VALID_SHA,
        adapter=_StubAdapter(_make_sections(18)),
    )
    assert result.exit_code == 0, result.error


# ---------------------------------------------------------------------------
# 6. Round name R1 format (minimal)
# ---------------------------------------------------------------------------


def test_round_name_minimal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1 minimal format validates correctly."""
    monkeypatch.chdir(tmp_path)
    result = run(
        round_name="R1",
        round_type="entry-admin",
        prior_round_anchor=_VALID_SHA,
        adapter=_StubAdapter(_make_sections(10)),
    )
    assert result.exit_code == 0, result.error


# ---------------------------------------------------------------------------
# 7. Template size — substrate-touching → 18
# ---------------------------------------------------------------------------


def test_template_size_substrate_touching() -> None:
    """substrate-touching maps to 18-section template."""
    assert _ROUND_TYPE_TO_TEMPLATE_SIZE["substrate-touching"] == 18
    assert _template_size_label("substrate-touching") == "full"


# ---------------------------------------------------------------------------
# 8. Template size — fix-round → 12
# ---------------------------------------------------------------------------


def test_template_size_fix_round() -> None:
    """fix-round maps to 12-section template."""
    assert _ROUND_TYPE_TO_TEMPLATE_SIZE["fix-round"] == 12
    assert _template_size_label("fix-round") == "narrow"


# ---------------------------------------------------------------------------
# 9. Template size — entry-admin → 10
# ---------------------------------------------------------------------------


def test_template_size_entry_admin() -> None:
    """entry-admin maps to 10-section template."""
    assert _ROUND_TYPE_TO_TEMPLATE_SIZE["entry-admin"] == 10
    assert _template_size_label("entry-admin") == "admin"


# ---------------------------------------------------------------------------
# 10. Template size — meta-admin-sweep → 10 (spec note: not 8)
# ---------------------------------------------------------------------------


def test_template_size_meta_admin_sweep() -> None:
    """meta-admin-sweep maps to 10-section for v0.2.0 P0 (8-section deferred)."""
    assert _ROUND_TYPE_TO_TEMPLATE_SIZE["meta-admin-sweep"] == 10
    assert _template_size_label("meta-admin-sweep") == "admin"


# ---------------------------------------------------------------------------
# 11. Brief construction: dispatched prompt contains required fields
# ---------------------------------------------------------------------------


def test_brief_construction_contains_required_fields() -> None:
    """Brief contains round_name, round_type, anchor, and template_size_label."""
    brief = _build_planner_brief(
        round_name="R5.2",
        round_type="substrate-touching",
        prior_round_anchor=_VALID_SHA,
        scope_description="Add auth module.",
        template_size_label="full",
        prior_handoff_summary="",
    )
    assert "R5.2" in brief
    assert "substrate-touching" in brief
    assert _VALID_SHA in brief
    assert "full" in brief
    assert "Add auth module." in brief


# ---------------------------------------------------------------------------
# 12. Planner output section-count mismatch → exit_code=1
# ---------------------------------------------------------------------------


def test_section_count_mismatch_returns_exit_code_1() -> None:
    """Stub returns 5-section output for substrate-touching → exit_code=1."""
    stub = _StubAdapter(_make_sections(5))  # wrong count for substrate-touching
    result = run(
        round_name="R1.0",
        round_type="substrate-touching",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 1
    assert result.error is not None
    assert "section" in result.error.lower() or "18" in result.error


# ---------------------------------------------------------------------------
# 13. Successful run — substrate-touching
# ---------------------------------------------------------------------------


def test_successful_substrate_touching(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub returns 18-section output; file written, RunResult fields populated."""
    monkeypatch.chdir(tmp_path)
    stub = _StubAdapter(_make_sections(18))
    result = run(
        round_name="R1.0",
        round_type="substrate-touching",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 0, result.error
    assert result.section_count == 18
    assert result.loc > 0
    assert result.handoff_path is not None
    assert result.handoff_path.exists()
    assert "R1.0" in str(result.handoff_path)


# ---------------------------------------------------------------------------
# 14. TBD/TODO marker warning — non-fatal (exit_code=0)
# ---------------------------------------------------------------------------


def test_tbd_marker_produces_warning_not_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """18-section output with TBD marker → warnings list populated, exit_code=0."""
    monkeypatch.chdir(tmp_path)
    canned = _make_sections(18) + "\nTBD: fill this in later"
    stub = _StubAdapter(canned)
    result = run(
        round_name="R2.0",
        round_type="substrate-touching",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 0, result.error
    assert len(result.warnings) >= 1
    assert any("TBD" in w for w in result.warnings)


def test_todo_marker_produces_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """18-section output with TODO marker → warnings list populated."""
    monkeypatch.chdir(tmp_path)
    canned = _make_sections(18) + "\nTODO: implement later"
    stub = _StubAdapter(canned)
    result = run(
        round_name="R2.1",
        round_type="substrate-touching",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 0, result.error
    assert any("TODO" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# 15. Prior handoff read — missing (no docs/superpowers/plans/ dir)
# ---------------------------------------------------------------------------


def test_prior_handoff_missing_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No docs/superpowers/plans/ dir → returns gracefully (empty prior_summary)."""
    monkeypatch.chdir(tmp_path)
    # No plans dir exists in tmp_path — function must not crash
    stub = _StubAdapter(_make_sections(10))
    result = run(
        round_name="R1",
        round_type="entry-admin",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 0, result.error


# ---------------------------------------------------------------------------
# 16. Prior handoff read — present (file contains anchor)
# ---------------------------------------------------------------------------


def test_prior_handoff_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """docs/superpowers/plans/ file containing the anchor → non-empty summary."""
    monkeypatch.chdir(tmp_path)
    plans_dir = tmp_path / "docs" / "superpowers" / "plans"
    plans_dir.mkdir(parents=True)
    prior_sha = "b" * 40
    (plans_dir / "2026-05-01-R0-handoff.md").write_text(
        f"# Prior Round\n\nanchor: {prior_sha}\n",
        encoding="utf-8",
    )
    # The brief should contain the prior_summary (non-empty)
    # We verify indirectly: run completes successfully
    stub = _StubAdapter(_make_sections(12))
    result = run(
        round_name="R1.1",
        round_type="fix-round",
        prior_round_anchor=prior_sha,
        adapter=stub,
    )
    assert result.exit_code == 0, result.error


# ---------------------------------------------------------------------------
# 17. Adapter parameter injection
# ---------------------------------------------------------------------------


def test_custom_adapter_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom adapter passed via `run(..., adapter=stub)` is used (not detect_adapter())."""
    monkeypatch.chdir(tmp_path)
    call_log: list[str] = []

    class _TrackingStub(_StubAdapter):
        def __init__(self) -> None:
            super().__init__(_make_sections(10))

        def dispatch_agent(
            self,
            agent_name: str,
            prompt: str,
            timeout_seconds: int = 600,
            isolation: Literal["worktree"] | None = None,
        ) -> AgentDispatchResult:
            call_log.append(agent_name)
            return super().dispatch_agent(agent_name, prompt, timeout_seconds, isolation)

    stub = _TrackingStub()
    result = run(
        round_name="R1",
        round_type="close-admin",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 0, result.error
    assert call_log == ["planner"]  # planner was dispatched exactly once


# ---------------------------------------------------------------------------
# 18. RunResult.summary() formatting
# ---------------------------------------------------------------------------


def test_run_result_summary_success(tmp_path: Path) -> None:
    """summary() for success case produces readable string with path + counts."""
    path = tmp_path / "docs" / "superpowers" / "plans" / "2026-05-13-R1-handoff.md"
    result = RunResult(
        handoff_path=path,
        section_count=18,
        loc=250,
        warnings=[],
        exit_code=0,
        error=None,
    )
    summary = result.summary()
    assert "plan-round succeeded" in summary
    assert "18" in summary
    assert "250" in summary


def test_run_result_summary_failure() -> None:
    """summary() for failure case produces FAILED: <error> string."""
    result = RunResult(
        handoff_path=None,
        section_count=0,
        loc=0,
        warnings=[],
        exit_code=2,
        error="Invalid round_type: 'foobar'.",
    )
    summary = result.summary()
    assert summary.startswith("FAILED:")
    assert "foobar" in summary


def test_run_result_summary_with_warnings(tmp_path: Path) -> None:
    """summary() with warnings includes warning count."""
    path = tmp_path / "handoff.md"
    result = RunResult(
        handoff_path=path,
        section_count=12,
        loc=180,
        warnings=["Output contains `TBD` marker"],
        exit_code=0,
        error=None,
    )
    summary = result.summary()
    assert "warnings" in summary
    assert "TBD" in summary


# ---------------------------------------------------------------------------
# Additional: validate_inputs raises PlanRoundError correctly
# ---------------------------------------------------------------------------


def test_validate_inputs_raises_for_bad_sha() -> None:
    """_validate_inputs raises PlanRoundError for non-hex SHA."""
    with pytest.raises(PlanRoundError, match="prior_round_anchor"):
        _validate_inputs("R1.0", "fix-round", "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")


def test_validate_inputs_passes_for_valid_inputs() -> None:
    """_validate_inputs does not raise for fully valid inputs."""
    _validate_inputs("R10-L3-aletheia", "substrate-touching", _VALID_SHA)  # must not raise


def test_planner_dispatch_failure_returns_exit_code_1() -> None:
    """When dispatch_agent returns exit_code != 0, run() returns exit_code=1."""
    stub = _StubAdapter(
        canned_output="",
        exit_code=1,
        error="planner timed out",
    )
    result = run(
        round_name="R1.0",
        round_type="fix-round",
        prior_round_anchor=_VALID_SHA,
        adapter=stub,
    )
    assert result.exit_code == 1
    assert result.error is not None
    assert "dispatch failed" in result.error or "planner" in result.error.lower()
