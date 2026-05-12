"""Tests for arcgentic.skills_impl.execute_round.

TDD: this file is written BEFORE execute_round.py exists.
Run order:
  1. pytest tests/unit/skills_impl/test_execute_round.py  → FAIL (ImportError)
  2. create execute_round.py
  3. pytest tests/unit/skills_impl/test_execute_round.py  → PASS

Uses _MultiStubAdapter (overrides InlineAdapter per-agent) to inject canned
outputs for each dispatched sub-agent without real `claude` subprocess calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest as _pytest

from arcgentic.adapters.base import AgentDispatchResult  # noqa: I001
from arcgentic.adapters.inline import InlineAdapter
from arcgentic.skills_impl.execute_round import (
    ExecuteRoundError,
    ExecuteRoundResult,
    _audit_handoff_path,
    _ba_design_path,
    _extract_ba_brief_from_handoff,
    _extract_se_threat_surfaces,
    _phase_dev_body,
    _phase_entry_admin,
    _round_to_upper,
    _run_quality_gates,
    run,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MINIMAL_HANDOFF = """\
# R10-L3-aletheia — Test Handoff

## 1. Scope

Round test scope.

## 2. References

| Ref | Path | Purpose | Status |
|---|---|---|---|
| R-1 | scripts/lib/state.sh | state lib | stable |

## 3. Prior round

Prior anchor: aaaa1234.

## 4. BA design pass brief

The BA design pass for this round should address the following:
- Design the main module interface
- Define the data model for state transitions
- Specify the public API surface

## 5. Commit plan

Commit 1: scaffolding.

## 6. Risk

Low.

## 7. Acceptance

Criteria: all tests pass.

## 8. Forward-debts

None.

## 9. QA

Run pytest.

## 10. Notes

None.

## 11. Sign-off

Planner agent.

## 12. Audit facts

25-40 mechanical facts.

## 13. CR targets

Review scope.

## 14. Security threat surfaces

### 14.1 Input validation

Validate all user inputs.

### 14.2 File system access

Restrict file reads to repo root.

### 14.3 Shell injection

Sanitize shell commands.

### 14.4 Agent output trust

Treat agent output as untrusted.

### 14.5 Secrets in output

Check for credential leakage.

## 15. SE contract

Contract text placeholder.

## 16. Release

Version bump.

## 17. Toolchain

Python 3.13+.

## 18. Final checklist

All checks green.

*substrate-touching handoff written by planner agent (arcgentic v0.2.0-alpha.1).*
"""

_CANNED_BA_DESIGN = """\
# R10-L3-aletheia — BA Design

## D-1. Module interface

Define a clean interface for the main module.

## D-2. Data model

State transitions use YAML.
"""

_CANNED_DEV_OUTPUT = """\
Implemented all files per BA design.

Files written:
- toolkit/src/arcgentic/core.py
- toolkit/tests/unit/test_core.py
"""

_CANNED_CR_OUTPUT = """\
## CR Findings

| CR-001 | P2 | Missing type hint on return value | file.py:10 |
| CR-002 | P3 | Long line | file.py:20 |
| CR-003 | P3 | Missing docstring | file.py:30 |
"""

_CANNED_SE_OUTPUT = """\
## SE Findings

| SE-001 | P1 | Shell injection risk in shell() wrapper | execute_round.py:40 |
| SE-002 | P3 | Agent output not sanitized before use | execute_round.py:80 |
"""


class _MultiStubAdapter(InlineAdapter):
    """Stub that returns different canned outputs per agent_name.

    shell() is mocked to return PASS for quality gates and sensible values
    for git operations.
    """

    def __init__(
        self,
        canned_outputs: dict[str, str],
        exit_codes: dict[str, int] | None = None,
        shell_overrides: dict[str, tuple[str, int]] | None = None,
        git_commit_sha: str = "abcd1234ef5678901234abcd1234ef5678901234",
    ) -> None:
        self._canned = canned_outputs
        self._exit_codes = exit_codes or {}
        self._shell_overrides = shell_overrides or {}
        self._git_commit_sha = git_commit_sha
        self._dispatched: list[str] = []

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: Literal["worktree"] | None = None,
    ) -> AgentDispatchResult:
        self._dispatched.append(agent_name)
        return AgentDispatchResult(
            output=self._canned.get(agent_name, ""),
            exit_code=self._exit_codes.get(agent_name, 0),
            duration_ms=10,
            agent_type=agent_name,
            error=None if self._exit_codes.get(agent_name, 0) == 0 else "stub error",
        )

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        # Check shell_overrides first (keyed by substring)
        for key, result in self._shell_overrides.items():
            if key in command:
                return result
        # Default mocks for quality gates
        if "mypy" in command or "pytest" in command or "ruff" in command:
            return "ok", 0
        if "git rev-parse" in command:
            return "/tmp/test-repo", 0
        if "git diff" in command:
            return "file1.py\nfile2.py", 0
        return "", 0

    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        return self._git_commit_sha


def _make_default_stub(
    ba_output: str = _CANNED_BA_DESIGN,
    dev_output: str = _CANNED_DEV_OUTPUT,
    cr_output: str = _CANNED_CR_OUTPUT,
    se_output: str = _CANNED_SE_OUTPUT,
    exit_codes: dict[str, int] | None = None,
    shell_overrides: dict[str, tuple[str, int]] | None = None,
) -> _MultiStubAdapter:
    return _MultiStubAdapter(
        canned_outputs={
            "ba-designer": ba_output,
            "developer": dev_output,
            "cr-reviewer": cr_output,
            "se-contract": se_output,
        },
        exit_codes=exit_codes,
        shell_overrides=shell_overrides,
    )


# ---------------------------------------------------------------------------
# 1. Missing handoff → exit_code=2, error mentions handoff
# ---------------------------------------------------------------------------


def test_missing_handoff_returns_exit_code_2(tmp_path: Path) -> None:
    """handoff_path doesn't exist → exit_code=2, error mentions handoff."""
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=tmp_path / "missing.md",
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 2
    assert result.error is not None
    assert "handoff" in result.error.lower() or "Handoff" in result.error


# ---------------------------------------------------------------------------
# 2. dry_run full happy path — 4 PhaseResults, all commit_sha=None
# ---------------------------------------------------------------------------


def test_dry_run_happy_path(tmp_path: Path) -> None:
    """dry_run=True; all 4 phases complete; commit_sha=None everywhere."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    assert result.dry_run is True
    assert len(result.phases) == 4
    for phase in result.phases:
        assert phase.commit_sha is None, (
            f"Expected None commit_sha in dry_run for {phase.phase_name}"
        )


# ---------------------------------------------------------------------------
# 3. Phase 1 (entry-admin) — handoff path in files_touched
# ---------------------------------------------------------------------------


def test_phase1_entry_admin_records_handoff_path(tmp_path: Path) -> None:
    """Phase 1 result records handoff_path in files_touched."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    p1 = result.phases[0]
    assert p1.phase_name == "entry-admin"
    assert str(handoff) in p1.files_touched


# ---------------------------------------------------------------------------
# 4. Phase 2 (BA design) — dispatch + file written
# ---------------------------------------------------------------------------


def test_phase2_ba_design_written(tmp_path: Path) -> None:
    """ba-designer dispatched; BA design written to docs/design/{ROUND_UPPER}_BA_DESIGN.md."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    p2 = result.phases[1]
    assert p2.phase_name == "ba-design"
    assert p2.sub_agent_dispatched == "ba-designer"
    # BA design file should be written
    ba_path = _ba_design_path("R10-L3-aletheia", tmp_path)
    assert ba_path.exists(), f"BA design not found at {ba_path}"
    assert "BA Design" in ba_path.read_text()


# ---------------------------------------------------------------------------
# 5. Phase 3 (dev body) — quality gates run; gate 4 SKIPPED
# ---------------------------------------------------------------------------


def test_phase3_quality_gates_run_and_gate4_skipped(tmp_path: Path) -> None:
    """Phase 3 runs 3 quality gates (mypy/pytest/ruff); gate 4 recorded as SKIPPED."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    p3 = result.phases[2]
    assert p3.phase_name == "dev-body"
    assert p3.quality_gates.get("mypy") == "PASS"
    assert p3.quality_gates.get("pytest") == "PASS"
    assert p3.quality_gates.get("ruff") == "PASS"
    assert "SKIPPED" in p3.quality_gates.get("audit-check", ""), (
        f"Expected audit-check to be SKIPPED, got: {p3.quality_gates.get('audit-check')}"
    )


# ---------------------------------------------------------------------------
# 6. Phase 3 — CR findings count
# ---------------------------------------------------------------------------


def test_cr_findings_count(tmp_path: Path) -> None:
    """CR returns 3 | CR- rows; cr_findings_count = 3."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(cr_output=_CANNED_CR_OUTPUT)  # has 3 | CR- rows
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    assert result.cr_findings_count == 3


# ---------------------------------------------------------------------------
# 7. Phase 3 — SE NOVEL findings count
# ---------------------------------------------------------------------------


def test_se_findings_count(tmp_path: Path) -> None:
    """SE returns 2 | SE- rows; se_findings_count = 2."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(se_output=_CANNED_SE_OUTPUT)  # has 2 | SE- rows
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    assert result.se_findings_count == 2


# ---------------------------------------------------------------------------
# 8. MANDATE #20 enforcement — BA content in SE brief raises ExecuteRoundError
# ---------------------------------------------------------------------------


def test_mandate_20_enforcement_ba_in_dev_output(tmp_path: Path) -> None:
    """If developer output contains round-specific BA design marker, MANDATE #20 raises.

    The SE brief is built partly from dev_result.output (the contract surface).
    If that output accidentally carries the round-prefixed `{ROUND_UPPER}_BA_DESIGN` marker,
    the mandate #20 check should fire and return exit_code=1.
    """
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    # Developer output contains round-specific BA design marker — simulates accidental leak
    # round_name="R10-L3-aletheia" → round_upper="R10_L3_ALETHEIA"
    poisoned_dev_output = "Implemented core module.\nR10_L3_ALETHEIA_BA_DESIGN reference leaked.\n"
    stub = _make_default_stub(dev_output=poisoned_dev_output)
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 1
    assert result.error is not None
    assert "MANDATE #20" in result.error or "mandate" in result.error.lower()


# ---------------------------------------------------------------------------
# 9. Phase 4 — self-audit handoff written with § 1-8 sections
# ---------------------------------------------------------------------------


def test_phase4_audit_handoff_written(tmp_path: Path) -> None:
    """Phase 4 writes self-audit handoff at expected path; contains required sections."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    assert result.audit_handoff_path is not None
    audit_path = result.audit_handoff_path
    assert audit_path.exists(), f"Audit handoff not written at {audit_path}"
    content = audit_path.read_text()
    # Verify required sections are present
    for section in ("§ 1.", "§ 2.", "§ 3.", "§ 4.", "§ 5.", "§ 6.", "§ 7.", "§ 8."):
        assert section in content, f"Missing section {section} in audit handoff"


# ---------------------------------------------------------------------------
# 10. Phase 4 — DONE_WITH_CONCERNS verdict + gate 4 deviation
# ---------------------------------------------------------------------------


def test_phase4_done_with_concerns_verdict(tmp_path: Path) -> None:
    """Audit handoff contains DONE_WITH_CONCERNS verdict and gate 4 deviation note."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    content = result.audit_handoff_path.read_text()  # type: ignore[union-attr]
    assert "DONE_WITH_CONCERNS" in content
    assert "audit-check" in content.lower() or "gate 4" in content.lower()
    # Deviation should mention ER-AUDIT-GATE-4
    assert "ER-AUDIT-GATE-4" in content


# ---------------------------------------------------------------------------
# 11. ba-designer dispatch failure → exit_code=1, error mentions ba-designer
# ---------------------------------------------------------------------------


def test_ba_designer_failure_returns_exit_code_1(tmp_path: Path) -> None:
    """ba-designer returns exit_code=1 → ExecuteRoundResult exit_code=1."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(exit_codes={"ba-designer": 1})
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 1
    assert result.error is not None
    assert "ba-designer" in result.error.lower()


# ---------------------------------------------------------------------------
# 12. developer dispatch failure → exit_code=1, error mentions developer
# ---------------------------------------------------------------------------


def test_developer_failure_returns_exit_code_1(tmp_path: Path) -> None:
    """developer returns exit_code=1 → ExecuteRoundResult exit_code=1."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(exit_codes={"developer": 1})
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 1
    assert result.error is not None
    assert "developer" in result.error.lower()


# ---------------------------------------------------------------------------
# 13. cr-reviewer dispatch failure → exit_code=1
# ---------------------------------------------------------------------------


def test_cr_reviewer_failure_returns_exit_code_1(tmp_path: Path) -> None:
    """cr-reviewer returns exit_code=1 → ExecuteRoundResult exit_code=1."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(exit_codes={"cr-reviewer": 1})
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 1
    assert result.error is not None


# ---------------------------------------------------------------------------
# 14. se-contract dispatch failure → exit_code=1
# ---------------------------------------------------------------------------


def test_se_contract_failure_returns_exit_code_1(tmp_path: Path) -> None:
    """se-contract returns exit_code=1 → ExecuteRoundResult exit_code=1."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(exit_codes={"se-contract": 1})
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 1
    assert result.error is not None


# ---------------------------------------------------------------------------
# 15. Quality gate FAIL → exit_code=1 (fail-fast, no retry)
# ---------------------------------------------------------------------------


def test_quality_gate_mypy_fail_returns_exit_code_1(tmp_path: Path) -> None:
    """mypy gate fails → ExecuteRoundResult exit_code=1 (ER-RETRY: fail-fast)."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub(shell_overrides={"mypy": ("mypy error", 1)})
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 1
    assert result.error is not None
    assert "mypy" in result.error.lower() or "gate" in result.error.lower()


# ---------------------------------------------------------------------------
# 16. summary() formatting — dry_run includes "(DRY RUN)" prefix
# ---------------------------------------------------------------------------


def test_summary_dry_run_prefix(tmp_path: Path) -> None:
    """summary() for dry_run result includes '(DRY RUN)' prefix."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    summary = result.summary()
    assert "DRY RUN" in summary


# ---------------------------------------------------------------------------
# 17. summary() formatting — error case prefixed "FAILED:"
# ---------------------------------------------------------------------------


def test_summary_error_prefix() -> None:
    """summary() for error case starts with 'FAILED:'."""
    result = ExecuteRoundResult(
        round_name="R-test",
        phases=[],
        exit_code=2,
        error="Missing handoff.",
        dry_run=False,
    )
    assert result.summary().startswith("FAILED:")
    assert "Missing handoff" in result.summary()


# ---------------------------------------------------------------------------
# 18. _round_to_upper helper
# ---------------------------------------------------------------------------


def test_round_to_upper_dash_format() -> None:
    """'R10-L3-aletheia' → 'R10_L3_ALETHEIA'."""
    assert _round_to_upper("R10-L3-aletheia") == "R10_L3_ALETHEIA"


def test_round_to_upper_dot_format() -> None:
    """'R1.6.1' → 'R1.6.1' (dots are NOT converted)."""
    result = _round_to_upper("R1.6.1")
    # Dots stay; hyphens are replaced with underscores
    assert "R1.6.1" == result


# ---------------------------------------------------------------------------
# 19. _ba_design_path helper
# ---------------------------------------------------------------------------


def test_ba_design_path(tmp_path: Path) -> None:
    """_ba_design_path produces correct path."""
    p = _ba_design_path("R10-L3-aletheia", tmp_path)
    assert p == tmp_path / "docs" / "design" / "R10_L3_ALETHEIA_BA_DESIGN.md"


# ---------------------------------------------------------------------------
# 20. _audit_handoff_path helper
# ---------------------------------------------------------------------------


def test_audit_handoff_path(tmp_path: Path) -> None:
    """_audit_handoff_path produces correct path."""
    p = _audit_handoff_path("R10-L3-aletheia", tmp_path)
    assert p == tmp_path / "docs" / "audits" / "R10-L3-aletheia.md"


# ---------------------------------------------------------------------------
# 21. _extract_ba_brief_from_handoff helper
# ---------------------------------------------------------------------------


def test_extract_ba_brief_with_section4(tmp_path: Path) -> None:
    """Handoff with § 4 → returns § 4 body (not full handoff)."""
    brief = _extract_ba_brief_from_handoff(_MINIMAL_HANDOFF)
    # Should contain the § 4 content
    assert "BA design pass" in brief or "design pass" in brief
    # Should NOT contain text from § 5
    assert "Commit 1: scaffolding." not in brief


def test_extract_ba_brief_without_section4() -> None:
    """Handoff without ## 4. → returns full handoff as fallback."""
    minimal = "# Handoff\n\n## 1. Scope\n\nSome scope.\n"
    result = _extract_ba_brief_from_handoff(minimal)
    assert result == minimal  # fallback: return whole handoff


# ---------------------------------------------------------------------------
# 22. _extract_se_threat_surfaces helper
# ---------------------------------------------------------------------------


def test_extract_se_threat_surfaces(tmp_path: Path) -> None:
    """Handoff with § 14.1-14.5 → returns 5 threat surface strings."""
    surfaces = _extract_se_threat_surfaces(_MINIMAL_HANDOFF)
    assert len(surfaces) == 5
    assert any("14.1" in s for s in surfaces)
    assert any("14.5" in s for s in surfaces)


def test_extract_se_threat_surfaces_empty_handoff() -> None:
    """Handoff without § 14 → returns empty list."""
    surfaces = _extract_se_threat_surfaces("# Handoff\n\n## 1. Scope\n\nContent.\n")
    assert surfaces == []


# ---------------------------------------------------------------------------
# 23. Adapter parameter injection
# ---------------------------------------------------------------------------


def test_custom_adapter_is_used(tmp_path: Path) -> None:
    """`run(..., adapter=stub)` uses stub, not detect_adapter()."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    # All 4 agents should have been dispatched
    assert "ba-designer" in stub._dispatched
    assert "developer" in stub._dispatched
    assert "cr-reviewer" in stub._dispatched
    assert "se-contract" in stub._dispatched


# ---------------------------------------------------------------------------
# 24. repo_root parameter injection
# ---------------------------------------------------------------------------


def test_repo_root_anchors_paths(tmp_path: Path) -> None:
    """Paths in result are anchored to provided repo_root."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    assert result.audit_handoff_path is not None
    assert str(result.audit_handoff_path).startswith(str(tmp_path))


# ---------------------------------------------------------------------------
# 25. Forward-debts mentioned in warnings
# ---------------------------------------------------------------------------


def test_warnings_include_forward_debts(tmp_path: Path) -> None:
    """result.warnings mentions ER-AUDIT-GATE-4 forward-debt."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    # ER-AUDIT-GATE-4 must appear somewhere in warnings
    warnings_text = " ".join(result.warnings)
    assert "ER-AUDIT-GATE-4" in warnings_text, (
        f"Expected ER-AUDIT-GATE-4 in warnings. Got: {result.warnings}"
    )


# ---------------------------------------------------------------------------
# Bonus: PhaseResult structure
# ---------------------------------------------------------------------------


def test_phase_result_names(tmp_path: Path) -> None:
    """4 phases are named entry-admin / ba-design / dev-body / state-refresh (in order)."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    names = [p.phase_name for p in result.phases]
    assert names == ["entry-admin", "ba-design", "dev-body", "state-refresh"]


def test_state_refresh_phase_has_deviation(tmp_path: Path) -> None:
    """Phase 4 (state-refresh) records gate 4 SKIPPED as a deviation."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    p4 = result.phases[3]
    assert p4.phase_name == "state-refresh"
    assert len(p4.deviations) >= 1
    assert any("audit-check" in d or "SKIPPED" in d or "ER-AUDIT-GATE-4" in d
               for d in p4.deviations)


def test_audit_check_pass_is_false(tmp_path: Path) -> None:
    """ExecuteRoundResult.audit_check_pass is False (SKIPPED per v0.2.0 P0)."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    stub = _make_default_stub()
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    assert result.exit_code == 0, result.error
    assert result.audit_check_pass is False


# ---------------------------------------------------------------------------
# New tests for code-review fixes applied to 349b4e2
# ---------------------------------------------------------------------------


def test_run_quality_gates_handles_paths_with_spaces(tmp_path: Path) -> None:
    """repo_root with space in path must not break shell command construction."""
    captured_commands: list[str] = []

    class _CapturingStub(_MultiStubAdapter):
        def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
            captured_commands.append(command)
            return "ok", 0

    stub = _CapturingStub(canned_outputs={})
    repo_with_space = tmp_path / "Arc Studio" / "arcgentic"
    repo_with_space.mkdir(parents=True, exist_ok=True)
    _run_quality_gates(stub, repo_with_space)
    # Each captured command must use POSIX-quoting (single quotes) around the spaced path
    for cmd in captured_commands[:3]:  # first 3 are mypy/pytest/ruff
        assert "'" in cmd, f"command should be POSIX-quoted: {cmd}"
        assert "Arc Studio" in cmd


def test_phase_entry_admin_skips_when_handoff_already_committed(tmp_path: Path) -> None:
    """If handoff has no uncommitted changes, Phase 1 returns no-op PhaseResult."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text("# handoff", encoding="utf-8")

    class _CleanStub(_MultiStubAdapter):
        def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
            # git status returns empty → already-committed
            if "git status" in command:
                return "", 0
            return super().shell(command, timeout_seconds)

    stub = _CleanStub(canned_outputs={})
    result = _phase_entry_admin(stub, "R1.0", handoff, tmp_path, dry_run=False)
    assert result.commit_sha is None
    assert result.deviations is not None and len(result.deviations) >= 1
    assert "handoff already committed" in (result.deviations[0] if result.deviations else "")


def test_phase_dev_body_raises_on_empty_staged(tmp_path: Path) -> None:
    """Empty staged area after developer dispatch should raise ExecuteRoundError."""
    class _EmptyStagedStub(_MultiStubAdapter):
        def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
            if "git diff --staged" in command:
                return "", 0  # empty — no staged files
            if "mypy" in command or "pytest" in command or "ruff" in command:
                return "ok", 0
            return super().shell(command, timeout_seconds)

    stub = _EmptyStagedStub(canned_outputs={
        "developer": "dev output",
        "cr-reviewer": "| CR-1 | P3 | ok | inline |",
        "se-contract": "| SE-1 | P3 | ok | ok | inline |",
    })
    # Write a minimal handoff for _phase_dev_body to consume
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")
    with _pytest.raises(ExecuteRoundError, match="no staged files"):
        _phase_dev_body(
            stub,
            "R1.0",
            "BA design content",
            _MINIMAL_HANDOFF,
            tmp_path,
            dry_run=False,
        )


def test_mandate_20_allows_benign_ba_design_substring(tmp_path: Path) -> None:
    """Benign substring `config_BA_DESIGN` should NOT trigger MANDATE #20 violation."""
    handoff = tmp_path / "handoff.md"
    handoff.write_text(_MINIMAL_HANDOFF, encoding="utf-8")

    stub = _MultiStubAdapter(canned_outputs={
        "ba-designer": "# R10_L3_ALETHEIA_BA_DESIGN\n\nBA content\n",
        # Dev output has benign substring (NOT round-prefixed — should not fire M#20)
        "developer": "config_BA_DESIGN_constant = 42  # benign use of substring",
        "cr-reviewer": "| CR-1 | P3 | ok | inline |",
        "se-contract": "| SE-1 | P3 | ok | ok | inline |",
    })
    result = run(
        round_name="R10-L3-aletheia",
        handoff_path=handoff,
        dry_run=True,
        adapter=stub,
        repo_root=tmp_path,
    )
    # Should NOT raise; benign substring != round-specific marker R10_L3_ALETHEIA_BA_DESIGN
    assert result.exit_code == 0, result.error
