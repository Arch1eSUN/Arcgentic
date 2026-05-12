"""VSCode + Codex adapter.

When arcgentic skills/CLI run inside VSCode with the Codex extension active,
this adapter uses Codex's `agent dispatch` CLI command to spawn sub-agents
and `skill invoke` to invoke skills.

Wire format: `codex agent dispatch <agent_name> <prompt>` for agents,
`codex skill invoke <skill_name> <args>` for skills.

Structurally identical to CodexCLIAdapter; difference is purely contextual
(env detection). The distinct platform_name ("vscode-codex" vs "codex-cli")
allows `detect_adapter()` to distinguish the two environments.

Filesystem / shell / git methods delegate to _local_env shared helpers.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.4
"""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import Literal

from . import _local_env
from .base import AgentDispatchResult


class VSCodeCodexAdapter:
    """Concrete IDEAdapter for VSCode with Codex extension."""

    platform_name = "vscode-codex"

    def __init__(self, codex_binary: str = "codex") -> None:
        """Create a VSCodeCodexAdapter.

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
        """Invoke a skill via `codex skill invoke <skill_name> [<args>]`.

        Raises RuntimeError if codex is not on PATH, exits non-zero, or times out.
        When `args` is empty, it is omitted from the subprocess argv entirely —
        passing "" as a positional arg is ambiguous for the codex CLI.
        """
        if not shutil.which(self._codex_binary):
            raise RuntimeError(f"`{self._codex_binary}` not found on PATH")

        cmd = [self._codex_binary, "skill", "invoke", skill_name]
        if args:  # only append args if non-empty
            cmd.append(args)

        try:
            result = subprocess.run(
                cmd,
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
