"""Tests for arcgentic.adapters.codex_cli — CodexCLIAdapter.

TDD: this file is written before codex_cli.py exists.
Run order:
  1. pytest tests/unit/adapters/test_codex_cli.py  → FAIL (ImportError)
  2. create codex_cli.py
  3. pytest tests/unit/adapters/test_codex_cli.py  → PASS

CodexCLIAdapter is structurally identical to VSCodeCodexAdapter but uses
platform_name='codex-cli'. Tests verify the distinct platform_name and
mirror the VSCodeCodexAdapter test structure for functional correctness.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arcgentic.adapters.base import IDEAdapter
from arcgentic.adapters.codex_cli import CodexCLIAdapter

# ---------------------------------------------------------------------------
# Test 1: platform_name
# ---------------------------------------------------------------------------


def test_platform_name() -> None:
    """CodexCLIAdapter.platform_name must equal 'codex-cli'."""
    adapter = CodexCLIAdapter()
    assert adapter.platform_name == "codex-cli"


# ---------------------------------------------------------------------------
# Test 2: Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_conformance() -> None:
    """CodexCLIAdapter must satisfy isinstance(adapter, IDEAdapter)."""
    adapter = CodexCLIAdapter()
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 3: distinct platform_name from VSCodeCodexAdapter
# ---------------------------------------------------------------------------


def test_platform_name_distinct_from_vscode_codex() -> None:
    """CodexCLIAdapter and VSCodeCodexAdapter must have different platform_names."""
    from arcgentic.adapters.vscode_codex import VSCodeCodexAdapter

    assert CodexCLIAdapter().platform_name != VSCodeCodexAdapter().platform_name


# ---------------------------------------------------------------------------
# Test 4: dispatch_agent success
# ---------------------------------------------------------------------------


def test_dispatch_agent_success() -> None:
    """dispatch_agent returns exit_code=0 and output on success."""
    adapter = CodexCLIAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = "codex-cli dispatch output"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.codex_cli.subprocess.run", return_value=mock_result):
            result = adapter.dispatch_agent("developer", "write tests")

    assert result.output == "codex-cli dispatch output"
    assert result.exit_code == 0
    assert result.error is None
    assert result.agent_type == "developer"


# ---------------------------------------------------------------------------
# Test 5: dispatch_agent non-zero exit
# ---------------------------------------------------------------------------


def test_dispatch_agent_failure() -> None:
    """dispatch_agent failure: error = stderr, exit_code non-zero."""
    adapter = CodexCLIAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "codex-cli error"
    mock_result.returncode = 2

    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.codex_cli.subprocess.run", return_value=mock_result):
            result = adapter.dispatch_agent("auditor", "audit")

    assert result.exit_code == 2
    assert result.error == "codex-cli error"


# ---------------------------------------------------------------------------
# Test 6: dispatch_agent timeout
# ---------------------------------------------------------------------------


def test_dispatch_agent_timeout() -> None:
    """dispatch_agent timeout: exit_code=124, error mentions 'timeout'."""
    adapter = CodexCLIAdapter(codex_binary="codex")

    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value="/usr/bin/codex"):
        with patch(
            "arcgentic.adapters.codex_cli.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=5),
        ):
            result = adapter.dispatch_agent("planner", "plan", timeout_seconds=5)

    assert result.exit_code == 124
    assert result.error is not None
    assert "timeout" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 7: dispatch_agent missing binary
# ---------------------------------------------------------------------------


def test_dispatch_agent_missing_binary() -> None:
    """dispatch_agent when binary not on PATH: exit_code=127."""
    adapter = CodexCLIAdapter(codex_binary="codex")
    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value=None):
        result = adapter.dispatch_agent("developer", "some prompt")

    assert result.exit_code == 127
    assert result.error is not None
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 8: invoke_skill success
# ---------------------------------------------------------------------------


def test_invoke_skill_success() -> None:
    """invoke_skill returns stdout on success."""
    adapter = CodexCLIAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = "skill output codex-cli"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.codex_cli.subprocess.run", return_value=mock_result):
            output = adapter.invoke_skill("pre-round-scan", "args")

    assert output == "skill output codex-cli"


# ---------------------------------------------------------------------------
# Test 9: invoke_skill failure
# ---------------------------------------------------------------------------


def test_invoke_skill_failure() -> None:
    """invoke_skill raises RuntimeError when codex exits non-zero."""
    adapter = CodexCLIAdapter(codex_binary="codex")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "skill failure"
    mock_result.returncode = 1

    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value="/usr/bin/codex"):
        with patch("arcgentic.adapters.codex_cli.subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="exited 1"):
                adapter.invoke_skill("verify-gates", "")


# ---------------------------------------------------------------------------
# Test 10: invoke_skill timeout
# ---------------------------------------------------------------------------


def test_invoke_skill_timeout() -> None:
    """invoke_skill raises RuntimeError on TimeoutExpired."""
    adapter = CodexCLIAdapter(codex_binary="codex")

    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value="/usr/bin/codex"):
        with patch(
            "arcgentic.adapters.codex_cli.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=600),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                adapter.invoke_skill("audit-round")


# ---------------------------------------------------------------------------
# Test 11: invoke_skill missing binary
# ---------------------------------------------------------------------------


def test_invoke_skill_missing_binary() -> None:
    """invoke_skill raises RuntimeError when codex binary not on PATH."""
    adapter = CodexCLIAdapter(codex_binary="codex")
    with patch("arcgentic.adapters.codex_cli.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not found"):
            adapter.invoke_skill("plan-round")


# ---------------------------------------------------------------------------
# Test dispatch_agent call_args pinning
# ---------------------------------------------------------------------------


def test_dispatch_agent_pins_call_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the exact subprocess command CodexCLIAdapter constructs.

    Identical wire format to VSCodeCodexAdapter — codex CLI's `agent dispatch`
    subcommand is platform-agnostic.
    """
    adapter = CodexCLIAdapter()
    monkeypatch.setattr(
        "arcgentic.adapters.codex_cli.shutil.which",
        lambda _: "/usr/local/bin/codex",
    )

    captured: dict[str, list[str]] = {}

    def _capture(args: list[str], **_kwargs: object) -> object:
        captured["cmd"] = args
        return type("R", (), {"stdout": "ok", "stderr": "", "returncode": 0})()

    monkeypatch.setattr(
        "arcgentic.adapters.codex_cli.subprocess.run", _capture
    )
    adapter.dispatch_agent("developer", "write a test")

    cmd = captured["cmd"]
    assert cmd == ["codex", "agent", "dispatch", "developer", "write a test"]


# ---------------------------------------------------------------------------
# Tests 12-13: filesystem delegation
# ---------------------------------------------------------------------------


def test_read_file_delegates(tmp_path: Path) -> None:
    """read_file delegates to _local_env.read_file."""
    target = tmp_path / "r.txt"
    target.write_text("codex-cli read", encoding="utf-8")
    adapter = CodexCLIAdapter()
    assert adapter.read_file(str(target)) == "codex-cli read"


def test_write_file_delegates(tmp_path: Path) -> None:
    """write_file delegates to _local_env.write_file."""
    target = tmp_path / "w.txt"
    adapter = CodexCLIAdapter()
    adapter.write_file(str(target), "codex-cli write")
    assert target.read_text(encoding="utf-8") == "codex-cli write"


def test_edit_file_delegates_to_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """edit_file delegates to _local_env.edit_file."""
    adapter = CodexCLIAdapter()
    calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        "arcgentic.adapters._local_env.edit_file",
        lambda p, o, n: calls.append((p, o, n)),
    )
    adapter.edit_file("/some/path", "old", "new")
    assert calls == [("/some/path", "old", "new")]


def test_shell_delegates_to_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """shell delegates to _local_env.shell."""
    adapter = CodexCLIAdapter()
    monkeypatch.setattr(
        "arcgentic.adapters._local_env.shell",
        lambda cmd, timeout_seconds: ("stub-out", 0),
    )
    out, code = adapter.shell("echo x")
    assert out == "stub-out"
    assert code == 0
