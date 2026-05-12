"""Inline adapter — fallback for environments without an LLM host.

When arcgentic skills/CLI run outside any supported IDE (Claude Code / Cursor /
VSCode-Codex / Codex CLI), `detect_adapter()` returns this adapter. It is intended
for:

- Test scenarios (each adapter test uses mocked subprocess; tests of the toolkit
  itself use InlineAdapter to exercise non-LLM-mediated methods)
- Headless arcgentic CLI usage where the user wants to inspect what an agent
  brief looks like without actually dispatching it
- Dry-run / dry-plan modes

Degraded semantics:
- `dispatch_agent`: returns the prompt unchanged with exit_code=0. The caller is
  responsible for actually executing the agent's intent (typically by reading
  the prompt and acting on it manually, or via a higher-level LLM invocation).
- `invoke_skill`: returns empty string + logs warning (no LLM host to invoke skill).
- Filesystem / shell / git: full functionality via _local_env.

Limitations: no subagent isolation; cost-discipline is irrelevant (zero LLM
calls). Production use of arcgentic skills with this adapter will NOT actually
dispatch agents — callers must arrange dispatch some other way.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.5 (fallback)
"""

from __future__ import annotations

import logging
from typing import Literal

from . import _local_env
from .base import AgentDispatchResult

_logger = logging.getLogger(__name__)


class InlineAdapter:
    """Fallback IDEAdapter for environments without an LLM host."""

    platform_name = "inline"

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: Literal["worktree"] | None = None,
    ) -> AgentDispatchResult:
        """Return the prompt unchanged with exit_code=0.

        Emits a WARNING log: no actual LLM dispatch occurs. Callers reading
        the result must execute the agent's intent manually (e.g., by presenting
        the prompt to the user for manual action, or via a higher-level invocation).

        `isolation` is accepted for API symmetry but has no effect.
        """
        _logger.warning(
            "InlineAdapter.dispatch_agent: no LLM host detected; returning prompt unchanged. "
            "Caller must execute agent intent manually for agent_name=%s",
            agent_name,
        )
        return AgentDispatchResult(
            output=prompt,
            exit_code=0,
            duration_ms=0,
            agent_type=agent_name,
            error=None,
        )

    def invoke_skill(self, skill_name: str, args: str = "") -> str:
        """Return '' — no LLM host available to invoke the skill.

        Emits a WARNING log. Callers should handle the empty-string return
        as a signal to arrange skill invocation some other way.
        """
        _logger.warning(
            "InlineAdapter.invoke_skill: no LLM host; cannot invoke /%s. Returning empty string.",
            skill_name,
        )
        return ""

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
