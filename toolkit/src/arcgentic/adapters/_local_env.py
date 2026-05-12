"""Shared local-environment helpers for IDEAdapter implementations.

These functions implement filesystem / shell / git operations that are identical
across all non-canonical IDE adapters (Cursor / VSCode-Codex / Codex CLI / Inline).
The canonical ClaudeCodeAdapter inlines these directly; a future cleanup task may
unify it with this module.

These are module-level functions (NOT a class) because they have no state — each
call is a fresh subprocess or filesystem op. Adapters call them as
`_local_env.read_file(path)` etc.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.3–§ 3.5
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def read_file(path: str) -> str:
    """Read a file and return its text content (utf-8)."""
    return Path(path).read_text(encoding="utf-8")


def write_file(path: str, content: str) -> None:
    """Write `content` to `path` (utf-8); creates or overwrites."""
    Path(path).write_text(content, encoding="utf-8")


def edit_file(path: str, old: str, new: str) -> None:
    """Replace exactly one occurrence of `old` with `new`.

    Raises ValueError on zero or multi-match (identical contract to
    ClaudeCodeAdapter.edit_file per spec § 3 IDEAdapter Protocol).
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        raise ValueError(f"edit_file: `old` not found in {path}")
    if count > 1:
        raise ValueError(f"edit_file: `old` appears {count} times in {path} (ambiguous)")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def shell(command: str, timeout_seconds: int = 120) -> tuple[str, int]:
    """Run a shell command; return (stdout, exit_code).

    On TimeoutExpired returns ('', 124) — same POSIX timeout convention as
    ClaudeCodeAdapter.shell.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "", 124


def _run_git(args: list[str], timeout_seconds: int = 60) -> tuple[str, str, int]:
    """Run `git <args>` via list-form subprocess (no shell=True).

    Returns (stdout, stderr, exit_code). Used by git_diff_staged / git_commit
    which need stderr for error diagnostics — shell() can't return stderr
    without breaking the IDEAdapter Protocol's tuple[str, int] signature.

    Underscore-prefix signals this is an internal helper; callers should use
    git_diff_staged() and git_commit() (the public surface).
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"git {args[0] if args else ''} timed out", 124


def git_diff_staged() -> str:
    """Return the output of `git diff --staged`.

    Raises RuntimeError if git exits non-zero (e.g., not in a git repo).
    """
    stdout, stderr, code = _run_git(["diff", "--staged"])
    if code != 0:
        raise RuntimeError(f"git diff --staged failed (exit {code}): {stderr.strip()}")
    return stdout


def git_commit(message: str, files: list[str] | None = None) -> str:
    """Stage `files` (if provided) then commit; return the new SHA.

    If `files` is None, commits whatever is already in the index.
    Does NOT use --no-verify / --no-gpg-sign / --amend per Protocol contract.
    """
    if files is not None:
        for f in files:
            _, stderr, code = _run_git(["add", "--", f])
            if code != 0:
                raise RuntimeError(f"git add {f} failed (exit {code}): {stderr.strip()}")

    _, stderr, code = _run_git(["commit", "-m", message])
    if code != 0:
        raise RuntimeError(f"git commit failed (exit {code}): {stderr.strip()}")

    stdout, stderr, code = _run_git(["rev-parse", "HEAD"])
    if code != 0:
        raise RuntimeError(f"git rev-parse HEAD failed (exit {code}): {stderr.strip()}")
    return stdout.strip()


def shquote(s: str) -> str:
    """POSIX single-quote escape for safe shell=True interpolation."""
    return "'" + s.replace("'", "'\\''") + "'"
