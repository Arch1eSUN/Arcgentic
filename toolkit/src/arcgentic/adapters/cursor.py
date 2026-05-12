"""Cursor adapter.

Per spec § 3.3, Cursor has no native subagent dispatch — but the cursor-agent CLI
(if installed) provides a similar facility. This adapter subprocesses to it.
Without the binary, `dispatch_agent` returns an error result (exit_code=127);
callers should check `exit_code` and fall back to InlineAdapter for environments
lacking isolation entirely.

`invoke_skill` is not natively supported in Cursor — this adapter raises
NotImplementedError. Users wanting skill-style invocation should compose with
ClaudeCodeAdapter or use Cursor's native /rules system.

NOTE: isinstance(CursorAdapter(), IDEAdapter) returns True because Protocol
runtime_checkable checks for method PRESENCE only, not whether they raise.
The method exists with the correct signature; that is sufficient for structural
conformance.

Filesystem / shell / git methods delegate to _local_env shared helpers.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.3
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Literal

from . import _local_env
from .base import AgentDispatchResult


class CursorAdapter:
    """Concrete IDEAdapter for Cursor."""

    platform_name = "cursor"

    def __init__(self, cursor_binary: str = "cursor-agent") -> None:
        """Create a CursorAdapter.

        `cursor_binary`: name (or path) of the cursor-agent CLI executable.
        Default "cursor-agent" assumes it's on PATH. Tests can inject a stub.
        """
        self._cursor_binary = cursor_binary

    # ── LLM-mediated methods ──────────────────────────────────────────────

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: Literal["worktree"] | None = None,
    ) -> AgentDispatchResult:
        """Dispatch a sub-agent via cursor-agent CLI.

        If cursor-agent binary is not on PATH, returns exit_code=127 with an
        informative error message. Callers should fall back to InlineAdapter.

        `isolation` parameter is accepted for API symmetry but has no effect
        (Cursor does not support worktree-based isolation).
        """
        if not shutil.which(self._cursor_binary):
            return AgentDispatchResult(
                output="",
                exit_code=127,
                duration_ms=0,
                agent_type=agent_name,
                error=(
                    f"`{self._cursor_binary}` not found on PATH "
                    "(Cursor lacks native subagent; install cursor-agent CLI or use InlineAdapter)"
                ),
            )

        wrapped = f"Acting as the {agent_name} agent:\n\n{prompt}"
        start = time.monotonic()
        try:
            result = subprocess.run(
                [self._cursor_binary, "--prompt", wrapped],
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
                exit_code=124,
                duration_ms=duration_ms,
                agent_type=agent_name,
                error=f"timeout after {timeout_seconds}s",
            )

    def invoke_skill(self, skill_name: str, args: str = "") -> str:
        """Not supported in Cursor — raises NotImplementedError.

        Cursor has no native skill registry. Users wanting skill-style invocation
        should compose with ClaudeCodeAdapter or implement via Cursor /rules.

        See spec § 3.3.
        """
        raise NotImplementedError(
            "Cursor has no native skill registry; compose with ClaudeCodeAdapter "
            "or implement via Cursor /rules. See spec § 3.3."
        )

    # ── Filesystem / shell / git via shared helpers ────────────────────────

    def read_file(self, path: str) -> str:
        return _local_env.read_file(path)

    def write_file(self, path: str, content: str) -> None:
        _local_env.write_file(path, content)

    def edit_file(self, path: str, old: str, new: str) -> None:
        _local_env.edit_file(path, old, new)

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        return _local_env.shell(command, timeout_seconds)

    def git_diff_staged(self) -> str:
        return _local_env.git_diff_staged()

    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        return _local_env.git_commit(message, files)
