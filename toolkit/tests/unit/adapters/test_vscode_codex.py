"""Tests for arcgentic.adapters.vscode_codex — VSCodeCodexAdapter.

TDD: this file is written before vscode_codex.py exists.
Run order:
  1. pytest tests/unit/adapters/test_vscode_codex.py  → FAIL (ImportError)
  2. create vscode_codex.py
  3. pytest tests/unit/adapters/test_vscode_codex.py  → PASS

Mocking strategy:
  - dispatch_agent / invoke_skill: patch shutil.which + subprocess.run in vscode_codex module
  - filesystem delegation: real tmp_path ops (delegates to _local_env, tested via real calls)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arcgentic.adapters.base import IDEAdapter
from arcgentic.adapters.vscode_codex import VSCodeCodexAdapter

# ---------------------------------------------------------------------------
# Test 1: platform_name
# ---------------------------------------------------------------------------


def test_platform_name() -> None:
    """VSCodeCodexAdapter.platform_name must equal 'vscode-codex'."""
    adapter = VSCodeCodexAdapter()
    assert adapter.platform_name == "vscode-codex"


# ---------------------------------------------------------------------------
# Test 2: Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_conformance() -> None:
    """VSCodeCodexAdapter must satisfy isinstance(adapter, IDEAdapter)."""
    adapter = VSCodeCodexAdapter()
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 3: dispatch_agent success
# ---------------------------------------------------------------------------


def test_dispatch_agent_success() -> None:
    """dispatch_agent returns exit_code=0 and output on success."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = "codex dispatch output"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.vscode_codex.subprocess.run", return_value=mock_result):
            result = adapter.dispatch_agent("developer", "write tests")

    assert result.output == "codex dispatch output"
    assert result.exit_code == 0
    assert result.error is None
    assert result.agent_type == "developer"


# ---------------------------------------------------------------------------
# Test 4: dispatch_agent non-zero exit
# ---------------------------------------------------------------------------


def test_dispatch_agent_failure() -> None:
    """dispatch_agent failure: error = stderr, exit_code non-zero."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "codex error"
    mock_result.returncode = 2

    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.vscode_codex.subprocess.run", return_value=mock_result):
            result = adapter.dispatch_agent("auditor", "audit")

    assert result.exit_code == 2
    assert result.error == "codex error"


# ---------------------------------------------------------------------------
# Test 5: dispatch_agent timeout
# ---------------------------------------------------------------------------


def test_dispatch_agent_timeout() -> None:
    """dispatch_agent timeout: exit_code=124, error mentions 'timeout'."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")

    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value="/usr/bin/codex"):
        with patch(
            "arcgentic.adapters.vscode_codex.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=5),
        ):
            result = adapter.dispatch_agent("planner", "plan", timeout_seconds=5)

    assert result.exit_code == 124
    assert result.error is not None
    assert "timeout" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 6: dispatch_agent missing binary
# ---------------------------------------------------------------------------


def test_dispatch_agent_missing_binary() -> None:
    """dispatch_agent when binary not on PATH: exit_code=127."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")
    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value=None):
        result = adapter.dispatch_agent("developer", "some prompt")

    assert result.exit_code == 127
    assert result.error is not None
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 7: invoke_skill success
# ---------------------------------------------------------------------------


def test_invoke_skill_success() -> None:
    """invoke_skill returns stdout on success."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = "skill output"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.vscode_codex.subprocess.run", return_value=mock_result):
            output = adapter.invoke_skill("pre-round-scan", "args")

    assert output == "skill output"


# ---------------------------------------------------------------------------
# Test 8: invoke_skill failure (non-zero exit)
# ---------------------------------------------------------------------------


def test_invoke_skill_failure() -> None:
    """invoke_skill raises RuntimeError when codex exits non-zero."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "skill failure"
    mock_result.returncode = 1

    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.vscode_codex.subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="exited 1"):
                adapter.invoke_skill("verify-gates", "")


# ---------------------------------------------------------------------------
# Test 9: invoke_skill timeout
# ---------------------------------------------------------------------------


def test_invoke_skill_timeout() -> None:
    """invoke_skill raises RuntimeError on TimeoutExpired."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")

    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value="/usr/bin/codex"):
        with patch(
            "arcgentic.adapters.vscode_codex.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=600),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                adapter.invoke_skill("audit-round")


# ---------------------------------------------------------------------------
# Test 10: invoke_skill missing binary
# ---------------------------------------------------------------------------


def test_invoke_skill_missing_binary() -> None:
    """invoke_skill raises RuntimeError when codex binary not on PATH."""
    adapter = VSCodeCodexAdapter(codex_binary="codex")
    with patch("arcgentic.adapters.vscode_codex.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not found"):
            adapter.invoke_skill("plan-round")


# ---------------------------------------------------------------------------
# Tests 11-12: filesystem delegation
# ---------------------------------------------------------------------------


def test_read_file_delegates(tmp_path: Path) -> None:
    """read_file delegates to _local_env.read_file."""
    target = tmp_path / "r.txt"
    target.write_text("vscode codex read", encoding="utf-8")
    adapter = VSCodeCodexAdapter()
    assert adapter.read_file(str(target)) == "vscode codex read"


def test_write_file_delegates(tmp_path: Path) -> None:
    """write_file delegates to _local_env.write_file."""
    target = tmp_path / "w.txt"
    adapter = VSCodeCodexAdapter()
    adapter.write_file(str(target), "vscode codex write")
    assert target.read_text(encoding="utf-8") == "vscode codex write"
