"""Tests for arcgentic.adapters.claude_code — ClaudeCodeAdapter.

TDD: this file is written before claude_code.py exists.
Run order:
  1. pytest tests/unit/adapters/test_claude_code.py  → FAIL (ImportError)
  2. create claude_code.py
  3. pytest tests/unit/adapters/test_claude_code.py  → PASS (18+ tests)

Mocking strategy:
  - Tests 8–10, 12, 13: `patch("arcgentic.adapters.claude_code.subprocess.run")` — mocked
  - Tests 14–17:        real subprocess / real tmp_path git ops (skipped if git unavailable)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arcgentic.adapters.base import IDEAdapter
from arcgentic.adapters.claude_code import ClaudeCodeAdapter

# ---------------------------------------------------------------------------
# Test 1: platform_name attribute
# ---------------------------------------------------------------------------


def test_platform_name() -> None:
    """ClaudeCodeAdapter.platform_name must equal 'claude-code'."""
    adapter = ClaudeCodeAdapter()
    assert adapter.platform_name == "claude-code"


# ---------------------------------------------------------------------------
# Test 2: Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_conformance() -> None:
    """ClaudeCodeAdapter must pass isinstance(adapter, IDEAdapter)."""
    adapter = ClaudeCodeAdapter()
    assert isinstance(adapter, IDEAdapter), (
        "ClaudeCodeAdapter must satisfy the IDEAdapter Protocol"
    )


# ---------------------------------------------------------------------------
# Test 3: read_file
# ---------------------------------------------------------------------------


def test_read_file(tmp_path: Path) -> None:
    """read_file returns the file's text content."""
    target = tmp_path / "hello.txt"
    target.write_text("arcgentic rocks")
    adapter = ClaudeCodeAdapter()
    assert adapter.read_file(str(target)) == "arcgentic rocks"


# ---------------------------------------------------------------------------
# Test 4: write_file
# ---------------------------------------------------------------------------


def test_write_file(tmp_path: Path) -> None:
    """write_file creates the file with expected contents."""
    target = tmp_path / "output.txt"
    adapter = ClaudeCodeAdapter()
    adapter.write_file(str(target), "hello world")
    assert target.read_text() == "hello world"


def test_write_file_overwrites(tmp_path: Path) -> None:
    """write_file overwrites existing content."""
    target = tmp_path / "overwrite.txt"
    target.write_text("old content")
    adapter = ClaudeCodeAdapter()
    adapter.write_file(str(target), "new content")
    assert target.read_text() == "new content"


# ---------------------------------------------------------------------------
# Test 5: edit_file success
# ---------------------------------------------------------------------------


def test_edit_file_success(tmp_path: Path) -> None:
    """edit_file replaces a unique occurrence and writes back."""
    target = tmp_path / "edit.txt"
    target.write_text("The quick brown fox jumps over the lazy dog")
    adapter = ClaudeCodeAdapter()
    adapter.edit_file(str(target), "brown fox", "red cat")
    assert target.read_text() == "The quick red cat jumps over the lazy dog"


# ---------------------------------------------------------------------------
# Test 6: edit_file raises on missing old string
# ---------------------------------------------------------------------------


def test_edit_file_raises_on_missing(tmp_path: Path) -> None:
    """edit_file raises ValueError when `old` is not present in the file."""
    target = tmp_path / "nochange.txt"
    target.write_text("nothing special here")
    adapter = ClaudeCodeAdapter()
    with pytest.raises(ValueError, match="not found"):
        adapter.edit_file(str(target), "DOES NOT EXIST", "replacement")


# ---------------------------------------------------------------------------
# Test 7: edit_file raises on multi-match
# ---------------------------------------------------------------------------


def test_edit_file_raises_on_multi_match(tmp_path: Path) -> None:
    """edit_file raises ValueError when `old` appears more than once (ambiguous)."""
    target = tmp_path / "multi.txt"
    target.write_text("foo bar foo")
    adapter = ClaudeCodeAdapter()
    with pytest.raises(ValueError, match="times"):
        adapter.edit_file(str(target), "foo", "baz")


# ---------------------------------------------------------------------------
# Test 8: dispatch_agent success
# ---------------------------------------------------------------------------


def test_dispatch_agent_success() -> None:
    """dispatch_agent returns AgentDispatchResult with output / exit_code=0 / error=None."""
    adapter = ClaudeCodeAdapter(claude_binary="claude")
    mock_result = MagicMock()
    mock_result.stdout = "agent output here"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.claude_code.subprocess.run", return_value=mock_result) as m:
        with patch("arcgentic.adapters.claude_code.shutil.which", return_value="/usr/bin/claude"):
            result = adapter.dispatch_agent("auditor", "do an audit")

    m.assert_called_once()
    assert result.output == "agent output here"
    assert result.exit_code == 0
    assert result.error is None
    assert result.agent_type == "auditor"
    assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Test 9: dispatch_agent failure (non-zero exit)
# ---------------------------------------------------------------------------


def test_dispatch_agent_failure() -> None:
    """dispatch_agent failure: error is set to stderr, exit_code is non-zero."""
    adapter = ClaudeCodeAdapter(claude_binary="claude")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "boom"
    mock_result.returncode = 1

    with patch("arcgentic.adapters.claude_code.subprocess.run", return_value=mock_result):
        with patch("arcgentic.adapters.claude_code.shutil.which", return_value="/usr/bin/claude"):
            result = adapter.dispatch_agent("developer", "write code")

    assert result.exit_code == 1
    assert result.error == "boom"
    assert result.output == ""


# ---------------------------------------------------------------------------
# Test 10: dispatch_agent timeout
# ---------------------------------------------------------------------------


def test_dispatch_agent_timeout() -> None:
    """dispatch_agent timeout: exit_code=124, error mentions timeout."""
    adapter = ClaudeCodeAdapter(claude_binary="claude")

    with patch(
        "arcgentic.adapters.claude_code.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["claude"], timeout=5),
    ):
        with patch("arcgentic.adapters.claude_code.shutil.which", return_value="/usr/bin/claude"):
            result = adapter.dispatch_agent("planner", "plan this", timeout_seconds=5)

    assert result.exit_code == 124
    assert result.error is not None
    assert "timeout" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 11: dispatch_agent missing binary
# ---------------------------------------------------------------------------


def test_dispatch_agent_missing_binary() -> None:
    """dispatch_agent with nonexistent binary: exit_code=127, error mentions 'not found'."""
    adapter = ClaudeCodeAdapter(claude_binary="/nonexistent/bin/claude")
    result = adapter.dispatch_agent("auditor", "some prompt")
    assert result.exit_code == 127
    assert result.error is not None
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# Test 12: invoke_skill success
# ---------------------------------------------------------------------------


def test_invoke_skill_success() -> None:
    """invoke_skill returns stdout of the spawned session."""
    adapter = ClaudeCodeAdapter(claude_binary="claude")
    mock_result = MagicMock()
    mock_result.stdout = "skill output"
    mock_result.stderr = ""
    mock_result.returncode = 0

    with patch("arcgentic.adapters.claude_code.subprocess.run", return_value=mock_result):
        with patch("arcgentic.adapters.claude_code.shutil.which", return_value="/usr/bin/claude"):
            output = adapter.invoke_skill("pre-round-scan", "some args")

    assert output == "skill output"


# ---------------------------------------------------------------------------
# Test 13: invoke_skill failure
# ---------------------------------------------------------------------------


def test_invoke_skill_failure() -> None:
    """invoke_skill raises RuntimeError when the spawned session exits non-zero."""
    adapter = ClaudeCodeAdapter(claude_binary="claude")
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.stderr = "skill error"
    mock_result.returncode = 2

    with patch("arcgentic.adapters.claude_code.subprocess.run", return_value=mock_result):
        with patch("arcgentic.adapters.claude_code.shutil.which", return_value="/usr/bin/claude"):
            with pytest.raises(RuntimeError, match="exited 2"):
                adapter.invoke_skill("verify-gates", "")


# ---------------------------------------------------------------------------
# Test 13b: invoke_skill timeout
# ---------------------------------------------------------------------------


def test_invoke_skill_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """invoke_skill catches TimeoutExpired and raises RuntimeError (consistent
    exception contract with dispatch_agent's exit_code=124 path)."""
    adapter = ClaudeCodeAdapter()
    monkeypatch.setattr(
        "arcgentic.adapters.claude_code.shutil.which",
        lambda _: "/usr/local/bin/claude",
    )

    def _raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(
        "arcgentic.adapters.claude_code.subprocess.run", _raise_timeout
    )

    with pytest.raises(RuntimeError, match=r"timed out"):
        adapter.invoke_skill("plan-round", "R10-test")


# ---------------------------------------------------------------------------
# Test 14: shell (real subprocess)
# ---------------------------------------------------------------------------


def test_shell_echo() -> None:
    """shell runs a real `echo hello` and captures stdout."""
    adapter = ClaudeCodeAdapter()
    output, code = adapter.shell("echo hello")
    assert code == 0
    assert output.strip().startswith("hello")


# ---------------------------------------------------------------------------
# Test 15: shell timeout (real subprocess)
# ---------------------------------------------------------------------------


def test_shell_timeout() -> None:
    """shell times out a long-running command: returns ('', 124)."""
    adapter = ClaudeCodeAdapter()
    output, code = adapter.shell("sleep 10", timeout_seconds=1)
    assert code == 124
    assert output == ""


# ---------------------------------------------------------------------------
# Test 16: git_diff_staged (real git in tmp_path)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
def test_git_diff_staged(tmp_path: Path) -> None:
    """git_diff_staged returns non-empty diff after staging a file."""
    # init a bare-minimum git repo in tmp_path
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )

    # Create + stage a file
    staged = tmp_path / "staged.txt"
    staged.write_text("staged content\n")
    subprocess.run(["git", "add", "staged.txt"], check=True, capture_output=True, cwd=str(tmp_path))

    # Adapter must report the staged diff
    adapter = ClaudeCodeAdapter()
    original_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        diff = adapter.git_diff_staged()
    finally:
        os.chdir(original_cwd)

    assert "staged.txt" in diff
    assert "staged content" in diff


# ---------------------------------------------------------------------------
# Test 17: git_commit round-trip (real git in tmp_path)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
def test_git_commit_round_trip(tmp_path: Path) -> None:
    """git_commit with files=[...] stages + commits; returns 40-char SHA."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )

    # Write an initial commit so HEAD exists
    init_file = tmp_path / "init.txt"
    init_file.write_text("init\n")
    subprocess.run(["git", "add", "init.txt"], check=True, capture_output=True, cwd=str(tmp_path))
    subprocess.run(
        ["git", "commit", "-m", "init"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )

    # Now have adapter commit a second file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello from adapter\n")

    adapter = ClaudeCodeAdapter()
    original_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        sha = adapter.git_commit("test commit from adapter", files=["test.txt"])
    finally:
        os.chdir(original_cwd)

    assert len(sha) == 40, f"Expected 40-char SHA, got: {sha!r}"
    # Verify commit landed
    log_out = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        check=True, capture_output=True, text=True, cwd=str(tmp_path),
    ).stdout
    assert "test commit from adapter" in log_out


# ---------------------------------------------------------------------------
# Test 18: _shquote handles tricky values
# ---------------------------------------------------------------------------


def test_shquote_basic() -> None:
    """_shquote single-quote-escapes values with embedded single quotes."""
    # "it's" → "'it'\\''s'"
    result = ClaudeCodeAdapter._shquote("it's")
    # Verify the result, when interpreted by a shell, yields the original string
    output = subprocess.run(
        f"echo {result}",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "it's" in output


def test_shquote_dollar_sign() -> None:
    """_shquote must prevent shell variable expansion of $VAR."""
    # single-quoting means '$VAR' is literal, not expanded
    result = ClaudeCodeAdapter._shquote("$HOME")
    proc = subprocess.run(
        f"printf '%s' {result}",
        shell=True,
        capture_output=True,
        text=True,
    )
    # should literally output "$HOME", not the expanded home directory
    assert proc.stdout == "$HOME"
