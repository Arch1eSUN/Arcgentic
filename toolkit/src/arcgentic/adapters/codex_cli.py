"""Codex CLI adapter (standalone).

When arcgentic skills/CLI run outside VSCode but with the standalone Codex CLI
installed, this adapter is what `detect_adapter()` selects. It is structurally
identical to VSCodeCodexAdapter — both subprocess to the same `codex` binary
with the same `agent dispatch` / `skill invoke` wire format. The distinction is
purely contextual (which environment triggered the adapter selection).

Wire format: `codex agent dispatch <agent_name> <prompt>` for agents,
`codex skill invoke <skill_name> <args>` for skills.

The separate class (and separate file) is intentional — adapter-per-platform
design per spec § 3.5. Future v0.3 may unify common Codex-based logic into a
shared base, but for P0 we keep them explicit and symmetric.

Filesystem / shell / git methods delegate to _local_env shared helpers.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.5
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Literal

from . import _local_env
from .base import AgentDispatchResult


class CodexCLIAdapter:
    """Concrete IDEAdapter for standalone Codex CLI."""

    platform_name = "codex-cli"

    def __init__(self, codex_binary: str = "codex") -> None:
        """Create a CodexCLIAdapter.

        `codex_binary`: name (or path) of the codex CLI executable.
        Default "codex" assumes it's on PATH. Tests can inject a stub.
        """
        self._codex_binary = codex_binary

    # ── LLM-mediated methods ──────────────────────────────────────────────

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: Literal["worktree"] | None = None,
    ) -> AgentDispatchResult:
        """Dispatch a sub-agent via `codex agent dispatch <name> <prompt>`.

        If codex binary is not on PATH, returns exit_code=127 with an error.
        `isolation` is accepted for API symmetry but has no effect.
        """
        if not shutil.which(self._codex_binary):
            return AgentDispatchResult(
                output="",
                exit_code=127,
                duration_ms=0,
                agent_type=agent_name,
                error=f"`{self._codex_binary}` not found on PATH",
            )

        start = time.monotonic()
        try:
            result = subprocess.run(
                [self._codex_binary, "agent", "dispatch", agent_name, prompt],
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
        """Invoke a skill via `codex skill invoke <skill_name> <args>`.

        Raises RuntimeError if codex is not on PATH, exits non-zero, or times out.
        """
        if not shutil.which(self._codex_binary):
            raise RuntimeError(f"`{self._codex_binary}` not found on PATH")

        try:
            result = subprocess.run(
                [self._codex_binary, "skill", "invoke", skill_name, args],
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
