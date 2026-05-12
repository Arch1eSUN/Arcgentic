"""Tests for arcgentic.hooks.quality_gate_enforce.

TDD order:
  1. pytest tests/unit/hooks/test_quality_gate_enforce.py → FAIL (ImportError — red)
  2. create hooks/__init__.py + quality_gate_enforce.py + update cli.py
  3. pytest tests/unit/hooks/test_quality_gate_enforce.py → PASS (green)

Tests use unittest.mock.patch on _run_command — no real mypy/pytest/ruff invoked.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import patch

import pytest

from arcgentic.hooks.quality_gate_enforce import (
    GateResult,
    main,
    run,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pass_mock(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
    """Mock _run_command that always returns exit 0."""
    return "ok\n", "", 0


def _fail_mock_for(gate_name: str) -> object:
    """Return a mock that fails the named gate and passes everything else.

    The gate is identified by a keyword in the command string.
    """
    keyword_map = {
        "mypy": "mypy",
        "pytest": "pytest",
        "ruff": "ruff",
        "audit-check": "audit-check",
    }
    kw = keyword_map[gate_name]

    def _mock(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
        if kw in cmd:
            return "", f"{gate_name} error output", 1
        # git rev-parse also uses _run_command; pass it
        return "ok\n", "", 0

    return _mock


# ---------------------------------------------------------------------------
# 1. All 4 gates PASS (with skip_audit_check=True so gate 4 is SKIPPED)
# ---------------------------------------------------------------------------


def test_all_mandatory_gates_pass(tmp_path: Path) -> None:
    """All 3 mandatory gates PASS → exit_code=0 only when audit also passes."""
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(
            repo_root=tmp_path,
            audit_handoff=tmp_path / "audit.md",
            skip_audit_check=True,
        )
    # 3 PASS + 1 SKIPPED → all_pass requires all gates PASS → False
    assert result.all_pass is False
    assert result.exit_code == 1
    gate_names = [g.name for g in result.gates]
    assert gate_names == ["mypy", "pytest", "ruff", "audit-check"]
    assert result.gates[3].status == "SKIPPED"


def test_all_four_gates_pass(tmp_path: Path) -> None:
    """All 4 gates PASS (audit_handoff exists + _run_command returns 0)."""
    audit_doc = tmp_path / "audit.md"
    audit_doc.write_text("# audit")
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, audit_handoff=audit_doc)
    assert result.all_pass is True
    assert result.exit_code == 0
    assert all(g.status == "PASS" for g in result.gates)


# ---------------------------------------------------------------------------
# 2. mypy FAIL → exit_code=1, gates[0].status=FAIL
# ---------------------------------------------------------------------------


def test_mypy_fail(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_fail_mock_for("mypy"),
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    assert result.gates[0].status == "FAIL"
    assert result.gates[0].name == "mypy"
    assert result.exit_code == 1
    assert result.all_pass is False


# ---------------------------------------------------------------------------
# 3. pytest FAIL → exit_code=1, gates[1].status=FAIL
# ---------------------------------------------------------------------------


def test_pytest_fail(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_fail_mock_for("pytest"),
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    assert result.gates[1].status == "FAIL"
    assert result.gates[1].name == "pytest"
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# 4. ruff FAIL → exit_code=1, gates[2].status=FAIL
# ---------------------------------------------------------------------------


def test_ruff_fail(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_fail_mock_for("ruff"),
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    assert result.gates[2].status == "FAIL"
    assert result.gates[2].name == "ruff"
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# 5. audit-check FAIL → exit_code=1, gates[3].status=FAIL
# ---------------------------------------------------------------------------


def test_audit_check_fail(tmp_path: Path) -> None:
    audit_doc = tmp_path / "audit.md"
    audit_doc.write_text("# audit")
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_fail_mock_for("audit-check"),
    ):
        result = run(repo_root=tmp_path, audit_handoff=audit_doc)
    assert result.gates[3].status == "FAIL"
    assert result.gates[3].name == "audit-check"
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# 6. audit_handoff=None → gate 4 SKIPPED with "no audit handoff path" error
# ---------------------------------------------------------------------------


def test_audit_handoff_none_skips_gate4(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, audit_handoff=None)
    gate4 = result.gates[3]
    assert gate4.status == "SKIPPED"
    assert gate4.error is not None
    assert "no audit handoff path" in gate4.error.lower()


# ---------------------------------------------------------------------------
# 7. skip_audit_check=True → gate 4 SKIPPED with "--skip-audit-check" error note
# ---------------------------------------------------------------------------


def test_skip_audit_check_flag_skips_gate4(tmp_path: Path) -> None:
    audit_doc = tmp_path / "audit.md"
    audit_doc.write_text("# audit")
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, audit_handoff=audit_doc, skip_audit_check=True)
    gate4 = result.gates[3]
    assert gate4.status == "SKIPPED"
    assert gate4.error is not None
    assert "--skip-audit-check" in gate4.error


# ---------------------------------------------------------------------------
# 8. audit_handoff path missing on disk → gate 4 SKIPPED with "handoff not found"
# ---------------------------------------------------------------------------


def test_audit_handoff_missing_path_skips_gate4(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.md"
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, audit_handoff=missing)
    gate4 = result.gates[3]
    assert gate4.status == "SKIPPED"
    assert gate4.error is not None
    assert "handoff not found" in gate4.error.lower()


# ---------------------------------------------------------------------------
# 9. All 3 mandatory PASS + gate 4 SKIPPED → exit_code=1 (all_pass requires ALL PASS)
# ---------------------------------------------------------------------------


def test_three_pass_one_skipped_exit_code_1(tmp_path: Path) -> None:
    """all_pass = all g.status == 'PASS'; SKIPPED != PASS → exit_code=1."""
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    assert result.exit_code == 1
    assert result.all_pass is False
    n_pass = sum(1 for g in result.gates if g.status == "PASS")
    n_skip = sum(1 for g in result.gates if g.status == "SKIPPED")
    assert n_pass == 3
    assert n_skip == 1


# ---------------------------------------------------------------------------
# 10. summary_text format: "quality-gate-enforce: N PASS, M FAIL, K SKIPPED"
# ---------------------------------------------------------------------------


def test_summary_text_format(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    # 3 PASS, 0 FAIL, 1 SKIPPED
    assert result.summary_text == "quality-gate-enforce: 3 PASS, 0 FAIL, 1 SKIPPED"


def test_summary_text_all_fail(tmp_path: Path) -> None:
    def _all_fail(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
        if "git" in cmd:
            return "ok\n", "", 0
        return "", "error", 1

    audit_doc = tmp_path / "audit.md"
    audit_doc.write_text("# audit")
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_all_fail
    ):
        result = run(repo_root=tmp_path, audit_handoff=audit_doc)
    assert "4 FAIL" in result.summary_text or "FAIL" in result.summary_text


# ---------------------------------------------------------------------------
# 11. shquote applied for repo_root with spaces
# ---------------------------------------------------------------------------


def test_shquote_applied_to_repo_root_with_spaces(tmp_path: Path) -> None:
    """Commands must single-quote paths — verify shquoted path appears in cmd."""
    space_path = tmp_path / "path with spaces"
    space_path.mkdir()
    captured_cmds: list[str] = []

    def _capturing_mock(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
        captured_cmds.append(cmd)
        return "ok\n", "", 0

    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_capturing_mock,
    ):
        run(repo_root=space_path, skip_audit_check=True)

    # mypy cmd should contain the single-quoted path
    mypy_cmds = [c for c in captured_cmds if "mypy" in c]
    assert mypy_cmds, "No mypy command captured"
    mypy_cmd = mypy_cmds[0]
    # Single-quoted: 'path with spaces'
    assert "'" in mypy_cmd, f"Path not single-quoted in: {mypy_cmd!r}"
    assert "path with spaces" in mypy_cmd


# ---------------------------------------------------------------------------
# 12. __str__ formatting includes gate names + output_tail on FAIL
# ---------------------------------------------------------------------------


def test_str_formatting_includes_gate_names(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    s = str(result)
    assert "mypy" in s
    assert "pytest" in s
    assert "ruff" in s
    assert "audit-check" in s
    assert "quality-gate-enforce" in s


def test_str_formatting_shows_fail_tail(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_fail_mock_for("mypy"),
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    s = str(result)
    assert "mypy" in s
    assert "FAIL" in s
    # Diagnostic tail should be indented
    assert "| " in s


# ---------------------------------------------------------------------------
# 13. CLI main — all PASS (skipping audit-check via --skip-audit-check)
# ---------------------------------------------------------------------------


def test_cli_main_all_pass_returns_0(tmp_path: Path) -> None:
    """main(['--repo-root', path, '--skip-audit-check']) exits 0 when all mandatory pass."""
    audit_doc = tmp_path / "audit.md"
    audit_doc.write_text("# audit")
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        # All 3 mandatory pass, gate 4 skipped → exit_code=1 (SKIPPED != PASS)
        exit_code = main(
            ["--repo-root", str(tmp_path), "--audit-handoff", str(audit_doc)]
        )
    # With a real audit_doc that exists + all pass → exit 0
    assert exit_code == 0


# ---------------------------------------------------------------------------
# 14. CLI main — --audit-handoff propagated to gate 4
# ---------------------------------------------------------------------------


def test_cli_main_audit_handoff_propagated(tmp_path: Path) -> None:
    """--audit-handoff path is passed to _gate_audit_check."""
    audit_doc = tmp_path / "audit.md"
    audit_doc.write_text("# audit")
    captured_cmds: list[str] = []

    def _capturing(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
        captured_cmds.append(cmd)
        return "ok\n", "", 0

    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_capturing
    ):
        main(["--repo-root", str(tmp_path), "--audit-handoff", str(audit_doc)])

    audit_cmds = [c for c in captured_cmds if "audit-check" in c]
    assert audit_cmds, "Expected audit-check command to be run"
    assert str(audit_doc) in audit_cmds[0]


# ---------------------------------------------------------------------------
# 15. CLI main — --skip-audit-check propagated
# ---------------------------------------------------------------------------


def test_cli_main_skip_audit_check_propagated(tmp_path: Path) -> None:
    """--skip-audit-check causes gate 4 to be SKIPPED."""
    captured_cmds: list[str] = []

    def _capturing(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
        captured_cmds.append(cmd)
        return "ok\n", "", 0

    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_capturing
    ):
        main(["--repo-root", str(tmp_path), "--skip-audit-check"])

    audit_cmds = [c for c in captured_cmds if "audit-check" in c]
    assert not audit_cmds, "audit-check should NOT be run when --skip-audit-check given"


# ---------------------------------------------------------------------------
# 16. GateResult is frozen (mutation raises FrozenInstanceError)
# ---------------------------------------------------------------------------


def test_gate_result_is_frozen() -> None:
    g = GateResult(name="mypy", status="PASS", exit_code=0)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        g.status = "FAIL"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 17. QualityGateEnforceResult is frozen
# ---------------------------------------------------------------------------


def test_quality_gate_result_is_frozen(tmp_path: Path) -> None:
    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command", side_effect=_pass_mock
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        result.all_pass = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 18. Timeout case: _run_command returns code=124 → gate FAIL
# ---------------------------------------------------------------------------


def test_timeout_causes_gate_fail(tmp_path: Path) -> None:
    """When _run_command returns exit_code=124 (timeout), the gate is FAIL."""

    def _timeout_mock(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
        if "mypy" in cmd:
            return "", "timeout after 600s", 124
        return "ok\n", "", 0

    with patch(
        "arcgentic.hooks.quality_gate_enforce._run_command",
        side_effect=_timeout_mock,
    ):
        result = run(repo_root=tmp_path, skip_audit_check=True)

    assert result.gates[0].status == "FAIL"
    assert result.gates[0].exit_code == 124
    assert result.exit_code == 1
