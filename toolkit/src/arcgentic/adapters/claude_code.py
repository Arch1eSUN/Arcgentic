"""Claude Code adapter — canonical reference IDEAdapter implementation.

When arcgentic skills/CLI run inside (or alongside) a Claude Code installation,
this adapter is what `detect_adapter()` selects.

Implementation strategy:
- `dispatch_agent` + `invoke_skill`: subprocess `claude -p "<wrapped prompt>"` —
  each dispatch is a fresh, stateless Claude Code session (matches spec § 5
  stateless-agent principle). NOTE: consumes Claude Code subscription tokens per
  dispatch; documented cost trade-off.
- `read_file` / `write_file` / `edit_file`: Python filesystem APIs (no LLM
  mediation needed; spec § 3.2 says these "wrap" Read/Write/Edit but at the
  Python layer that means direct filesystem access).
- `shell`: subprocess.run with shell=True; timeout enforced.
- `git_diff_staged` / `git_commit`: subprocess git invocations.

Anti-contamination invariant (spec § 1.5) is preserved: dispatch_agent does NOT
inject tools= or tool_choice=; the prompt string is the only payload sent
to the spawned Claude Code session.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.2
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

from .base import AgentDispatchResult


class ClaudeCodeAdapter:
    """Concrete IDEAdapter for Claude Code."""

    platform_name = "claude-code"

    def __init__(self, claude_binary: str = "claude") -> None:
        """Create a ClaudeCodeAdapter.

        `claude_binary`: name (or path) of the `claude` CLI executable. Default
        "claude" assumes it's on PATH. Tests can inject a stub binary path.
        """
        self._claude_binary = claude_binary

    # ── LLM-mediated methods ──────────────────────────────────────────────

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: Literal["worktree"] | None = None,
    ) -> AgentDispatchResult:
        """Spawn `claude -p "<wrapped>"` with the agent brief.

        The wrapped prompt prefixes the brief with "Acting as the {agent_name}
        agent:\\n\\n" to nudge the spawned Claude Code session into the right role.
        Each dispatch is a fresh session; the spawned process inherits no context
        from the calling session.

        `isolation="worktree"` is currently a NO-OP for Claude Code (the spawned
        session inherits the caller's working directory). Future versions may wrap
        the call in `git worktree add` and clean up after; reserved for forward
        compatibility.
        """
        if not self._has_claude_binary():
            return AgentDispatchResult(
                output="",
                exit_code=127,
                duration_ms=0,
                agent_type=agent_name,
                error=f"`{self._claude_binary}` not found on PATH",
            )

        wrapped = f"Acting as the {agent_name} agent:\n\n{prompt}"
        start = time.monotonic()
        try:
            result = subprocess.run(
                [self._claude_binary, "-p", wrapped],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            error = result.stderr.strip() if result.returncode != 0 else None
            return AgentDispatchResult(
                output=result.stdout,
                exit_code=result.returncode,
                duration_ms=duration_ms,
                agent_type=agent_name,
                error=error,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            return AgentDispatchResult(
                output="",
                exit_code=124,  # POSIX timeout convention
                duration_ms=duration_ms,
                agent_type=agent_name,
                error=f"timeout after {timeout_seconds}s",
            )

    def invoke_skill(self, skill_name: str, args: str = "") -> str:
        """Invoke a skill by issuing the slash-command via `claude -p`.

        Wraps as "Invoke /{skill_name} {args}" — Claude Code interprets this as a
        skill invocation. Returns the stdout of the spawned session.
        """
        if not self._has_claude_binary():
            raise RuntimeError(f"`{self._claude_binary}` not found on PATH")

        prompt = f"Invoke /{skill_name} {args}".strip()
        try:
            result = subprocess.run(
                [self._claude_binary, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"/{skill_name} timed out after 600s") from None

        if result.returncode != 0:
            raise RuntimeError(
                f"`/{skill_name}` exited {result.returncode}: {result.stderr.strip()}"
            )
        return result.stdout

    # ── Filesystem (no LLM mediation) ─────────────────────────────────────

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> None:
        Path(path).write_text(content, encoding="utf-8")

    def edit_file(self, path: str, old: str, new: str) -> None:
        p = Path(path)
        text = p.read_text()
        count = text.count(old)
        if count == 0:
            raise ValueError(f"edit_file: `old` not found in {path}")
        if count > 1:
            raise ValueError(
                f"edit_file: `old` appears {count} times in {path} (ambiguous)"
            )
        p.write_text(text.replace(old, new, 1))

    # ── Shell + git ────────────────────────────────────────────────────────

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
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

    def git_diff_staged(self) -> str:
        stdout, stderr, code = self._run_git(["diff", "--staged"])
        if code != 0:
            raise RuntimeError(f"git diff --staged failed (exit {code}): {stderr.strip()}")
        return stdout

    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        if files is not None:
            # Stage explicitly listed files first.
            for f in files:
                _, stderr, code = self._run_git(["add", "--", f])
                if code != 0:
                    raise RuntimeError(f"git add {f} failed (exit {code}): {stderr.strip()}")

        # Commit using -m; avoid --no-verify / --no-gpg-sign / --amend per Protocol contract.
        _, stderr, code = self._run_git(["commit", "-m", message])
        if code != 0:
            raise RuntimeError(f"git commit failed (exit {code}): {stderr.strip()}")

        # Return the new commit SHA.
        stdout, stderr, code = self._run_git(["rev-parse", "HEAD"])
        if code != 0:
            raise RuntimeError(f"git rev-parse HEAD failed (exit {code}): {stderr.strip()}")
        return stdout.strip()

    # ── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _run_git(args: list[str], timeout_seconds: int = 60) -> tuple[str, str, int]:
        """Run `git <args>` via list-form subprocess (no shell).

        Returns (stdout, stderr, exit_code). Used by git-specific adapter methods
        that need stderr surfaced for error diagnostics. shell() can't return
        stderr without breaking the IDEAdapter Protocol's tuple[str, int] contract.
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

    def _has_claude_binary(self) -> bool:
        return shutil.which(self._claude_binary) is not None

    @staticmethod
    def _shquote(s: str) -> str:
        """Minimal shell-quoting (single-quote escape) for safe `shell=True` use."""
        return "'" + s.replace("'", "'\\''") + "'"
