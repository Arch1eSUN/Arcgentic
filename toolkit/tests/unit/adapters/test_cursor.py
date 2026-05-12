"""Tests for arcgentic.adapters.cursor — CursorAdapter.

TDD: this file is written before cursor.py exists.
Run order:
  1. pytest tests/unit/adapters/test_cursor.py  → FAIL (ImportError)
  2. create cursor.py
  3. pytest tests/unit/adapters/test_cursor.py  → PASS

Mocking strategy:
  - dispatch_agent tests: patch shutil.which + subprocess.run in cursor module
  - filesystem/git delegation tests: patch _local_env module-level functions
  - invoke_skill: verify NotImplementedError raised
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arcgentic.adapters.base import IDEAdapter
from arcgentic.adapters.cursor import CursorAdapter

# ---------------------------------------------------------------------------
# Test 1: platform_name
# ---------------------------------------------------------------------------


def test_platform_name() -> None:
    """CursorAdapter.platform_name must equal 'cursor'."""
    adapter = CursorAdapter()
    assert adapter.platform_name == "cursor"


# ---------------------------------------------------------------------------
# Test 2: Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_conformance() -> None:
    """CursorAdapter must satisfy isinstance(adapter, IDEAdapter).

    NOTE: runtime_checkable Protocol checks for method PRESENCE only, not
    whether they raise. invoke_skill raises NotImplementedError but the method
    EXISTS — isinstance must still return True.
    """
    adapter = CursorAdapter()
    assert isinstance(adapter, IDEAdapter), (
        "CursorAdapter must satisfy the IDEAdapter Protocol (structural, not semantic)"
    )


# ---------------------------------------------------------------------------
# Test 3: dispatch_agent success
# ---------------------------------------------------------------------------


def test_dispatch_agent_success() -> None:
    """dispatch_agent returns exit_code=0, output, no error on success."""
    adapter = CursorAdapter(cursor_binary="cursor-agent")
    mock_result = MagicMock()
    mock_result.stdout = "cursor agent output"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.cursor.shutil.which", return_value="/usr/bin/cursor-agent"):
        with patch("arcgentic.adapters.cursor.subprocess.run", return_value=mock_result):
            result = adapter.dispatch_agent("planner", "plan the round")

    assert result.output == "cursor agent output"
    assert result.exit_code == 0
    assert result.error is None
    assert result.agent_type == "planner"
    assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Test 4: dispatch_agent non-zero exit
# ---------------------------------------------------------------------------


def test_dispatch_agent_failure() -> None:
    """dispatch_agent failure: error set to stderr, exit_code non-zero."""
    adapter = CursorAdapter(cursor_binary="cursor-agent")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "cursor failed"
    mock_result.returncode = 1

    with patch("arcgentic.adapters.cursor.shutil.which", return_value="/usr/bin/cursor-agent"):
        with patch("arcgentic.adapters.cursor.subprocess.run", return_value=mock_result):
            result = adapter.dispatch_agent("developer", "write code")

    assert result.exit_code == 1
    assert result.error == "cursor failed"


# ---------------------------------------------------------------------------
# Test 5: dispatch_agent timeout
# ---------------------------------------------------------------------------


def test_dispatch_agent_timeout() -> None:
    """dispatch_agent timeout: exit_code=124, error mentions 'timeout'."""
    adapter = CursorAdapter(cursor_binary="cursor-agent")

    with patch("arcgentic.adapters.cursor.shutil.which", return_value="/usr/bin/cursor-agent"):
        with patch(
            "arcgentic.adapters.cursor.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["cursor-agent"], timeout=5),
        ):
            result = adapter.dispatch_agent("auditor", "audit this", timeout_seconds=5)

    assert result.exit_code == 124
    assert result.error is not None
    assert "timeout" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 6: dispatch_agent missing binary
# ---------------------------------------------------------------------------


def test_dispatch_agent_missing_binary() -> None:
    """dispatch_agent when binary not on PATH: exit_code=127, error mentions 'not found'."""
    adapter = CursorAdapter(cursor_binary="cursor-agent")
    with patch("arcgentic.adapters.cursor.shutil.which", return_value=None):
        result = adapter.dispatch_agent("auditor", "some prompt")

    assert result.exit_code == 127
    assert result.error is not None
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# Test dispatch_agent call_args pinning
# ---------------------------------------------------------------------------


def test_dispatch_agent_pins_call_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the exact subprocess command Cursor adapter constructs.

    CursorAdapter wraps the prompt with role-prefix because cursor-agent CLI does
    not accept agent_name as a separate parameter. This contract diverges from
    the codex adapters (which pass agent_name as a positional argv) and must be
    preserved.
    """
    adapter = CursorAdapter()
    monkeypatch.setattr(
        "arcgentic.adapters.cursor.shutil.which",
        lambda _: "/usr/local/bin/cursor-agent",
    )

    captured: dict[str, list[str]] = {}

    def _capture(args: list[str], **_kwargs: object) -> object:
        captured["cmd"] = args
        return type("R", (), {"stdout": "ok", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(
        "arcgentic.adapters.cursor.subprocess.run", _capture
    )
    adapter.dispatch_agent("developer", "write a test")

    cmd = captured["cmd"]
    assert cmd[0] == "cursor-agent"
    assert cmd[1] == "--prompt"
    assert "Acting as the developer agent:" in cmd[2]
    assert "write a test" in cmd[2]


# ---------------------------------------------------------------------------
# Test 7: invoke_skill raises NotImplementedError
# ---------------------------------------------------------------------------


def test_invoke_skill_raises_not_implemented() -> None:
    """invoke_skill must raise NotImplementedError — Cursor has no skill registry."""
    adapter = CursorAdapter()
    with pytest.raises(NotImplementedError):
        adapter.invoke_skill("pre-round-scan")


def test_invoke_skill_raises_not_implemented_with_args() -> None:
    """invoke_skill with args still raises NotImplementedError."""
    adapter = CursorAdapter()
    with pytest.raises(NotImplementedError):
        adapter.invoke_skill("verify-gates", "some args")


# ---------------------------------------------------------------------------
# Tests 8-11: filesystem/git delegation to _local_env
# ---------------------------------------------------------------------------


def test_read_file_delegates(tmp_path: Path) -> None:
    """read_file delegates to _local_env.read_file."""
    target = tmp_path / "r.txt"
    target.write_text("cursor read", encoding="utf-8")
    adapter = CursorAdapter()
    assert adapter.read_file(str(target)) == "cursor read"


def test_write_file_delegates(tmp_path: Path) -> None:
    """write_file delegates to _local_env.write_file."""
    target = tmp_path / "w.txt"
    adapter = CursorAdapter()
    adapter.write_file(str(target), "cursor write")
    assert target.read_text(encoding="utf-8") == "cursor write"


def test_edit_file_delegates(tmp_path: Path) -> None:
    """edit_file delegates to _local_env.edit_file."""
    target = tmp_path / "e.txt"
    target.write_text("old value", encoding="utf-8")
    adapter = CursorAdapter()
    adapter.edit_file(str(target), "old value", "new value")
    assert target.read_text(encoding="utf-8") == "new value"


def test_shell_delegates() -> None:
    """shell delegates to _local_env.shell."""
    adapter = CursorAdapter()
    with patch("arcgentic.adapters._local_env.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="hello\n", returncode=0)
        output, code = adapter.shell("echo hello")
    assert code == 0
