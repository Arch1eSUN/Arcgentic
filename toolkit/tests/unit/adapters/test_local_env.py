"""Tests for arcgentic.adapters._local_env — shared local-environment helpers.

TDD: this file is written before _local_env.py exists.
Run order:
  1. pytest tests/unit/adapters/test_local_env.py  → FAIL (ImportError)
  2. create _local_env.py
  3. pytest tests/unit/adapters/test_local_env.py  → PASS

All functions are module-level (not a class). Tests mirror the relevant
test_claude_code.py patterns to confirm functional parity.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from arcgentic.adapters import _local_env

# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


def test_read_file(tmp_path: Path) -> None:
    """read_file returns file text with utf-8 encoding."""
    target = tmp_path / "hello.txt"
    target.write_text("arcgentic _local_env", encoding="utf-8")
    assert _local_env.read_file(str(target)) == "arcgentic _local_env"


def test_read_file_unicode(tmp_path: Path) -> None:
    """read_file handles non-ASCII content correctly."""
    target = tmp_path / "unicode.txt"
    target.write_text("你好世界", encoding="utf-8")
    assert _local_env.read_file(str(target)) == "你好世界"


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


def test_write_file(tmp_path: Path) -> None:
    """write_file creates a file with expected content."""
    target = tmp_path / "out.txt"
    _local_env.write_file(str(target), "hello from _local_env")
    assert target.read_text(encoding="utf-8") == "hello from _local_env"


def test_write_file_overwrites(tmp_path: Path) -> None:
    """write_file overwrites existing content."""
    target = tmp_path / "over.txt"
    target.write_text("old", encoding="utf-8")
    _local_env.write_file(str(target), "new")
    assert target.read_text(encoding="utf-8") == "new"


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------


def test_edit_file_success(tmp_path: Path) -> None:
    """edit_file replaces a unique occurrence."""
    target = tmp_path / "edit.txt"
    target.write_text("The quick brown fox", encoding="utf-8")
    _local_env.edit_file(str(target), "brown fox", "red cat")
    assert target.read_text(encoding="utf-8") == "The quick red cat"


def test_edit_file_raises_on_missing(tmp_path: Path) -> None:
    """edit_file raises ValueError when `old` is not present."""
    target = tmp_path / "miss.txt"
    target.write_text("nothing here", encoding="utf-8")
    with pytest.raises(ValueError, match="not found"):
        _local_env.edit_file(str(target), "DOES NOT EXIST", "x")


def test_edit_file_raises_on_multi_match(tmp_path: Path) -> None:
    """edit_file raises ValueError when `old` appears more than once."""
    target = tmp_path / "multi.txt"
    target.write_text("foo bar foo", encoding="utf-8")
    with pytest.raises(ValueError, match="times"):
        _local_env.edit_file(str(target), "foo", "baz")


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------


def test_shell_echo() -> None:
    """shell runs `echo hello` and captures stdout."""
    output, code = _local_env.shell("echo hello")
    assert code == 0
    assert "hello" in output


def test_shell_timeout() -> None:
    """shell times out a long-running command: returns ('', 124)."""
    output, code = _local_env.shell("sleep 10", timeout_seconds=1)
    assert code == 124
    assert output == ""


# ---------------------------------------------------------------------------
# _run_git
# ---------------------------------------------------------------------------


def test__run_git_success() -> None:
    """_run_git executes `git --version` and returns exit_code=0."""
    stdout, stderr, code = _local_env._run_git(["--version"])
    assert code == 0
    assert "git" in stdout.lower()


def test__run_git_empty_args_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """_run_git handles TimeoutExpired for empty args list."""
    def _raise(*a: object, **k: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["git"], timeout=1)

    monkeypatch.setattr("arcgentic.adapters._local_env.subprocess.run", _raise)
    stdout, stderr, code = _local_env._run_git([])
    assert code == 124
    assert stdout == ""
    assert "timed out" in stderr


# ---------------------------------------------------------------------------
# git_diff_staged + git_commit (real git in tmp_path)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
def test_git_diff_staged(tmp_path: Path) -> None:
    """git_diff_staged returns non-empty diff after staging a file."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )
    staged = tmp_path / "staged.txt"
    staged.write_text("staged content\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], check=True, capture_output=True, cwd=str(tmp_path))

    original_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        diff = _local_env.git_diff_staged()
    finally:
        os.chdir(original_cwd)

    assert "staged.txt" in diff
    assert "staged content" in diff


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
    init_file = tmp_path / "init.txt"
    init_file.write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "init.txt"], check=True, capture_output=True, cwd=str(tmp_path))
    subprocess.run(
        ["git", "commit", "-m", "init"],
        check=True, capture_output=True, cwd=str(tmp_path),
    )

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello from _local_env\n", encoding="utf-8")

    original_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        sha = _local_env.git_commit("test commit from _local_env", files=["test.txt"])
    finally:
        os.chdir(original_cwd)

    assert len(sha) == 40, f"Expected 40-char SHA, got: {sha!r}"
    log_out = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        check=True, capture_output=True, text=True, cwd=str(tmp_path),
    ).stdout
    assert "test commit from _local_env" in log_out


# ---------------------------------------------------------------------------
# shquote
# ---------------------------------------------------------------------------


def test_shquote_basic() -> None:
    """shquote single-quote-escapes values with embedded single quotes."""
    result = _local_env.shquote("it's")
    output = subprocess.run(
        f"echo {result}",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "it's" in output


def test_shquote_dollar_sign() -> None:
    """shquote prevents shell variable expansion of $VAR."""
    result = _local_env.shquote("$HOME")
    proc = subprocess.run(
        f"printf '%s' {result}",
        shell=True,
        capture_output=True,
        text=True,
    )
    assert proc.stdout == "$HOME"
