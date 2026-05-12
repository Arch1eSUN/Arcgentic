"""IDE Adapter Protocol — the abstraction surface arcgentic skills/CLI use to talk
to whatever AI agent platform is hosting them (Claude Code / Cursor / VSCode-Codex /
Codex CLI / inline fallback).

Adding a new platform = implementing this Protocol; arcgentic skills/CLI then work
unchanged.

Anti-contamination invariant (spec § 1.5): adapter methods MUST NOT inject
`tools=` or `tool_choice=` at the agent level. Those belong one layer down
in the LLM-client layer.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AgentDispatchResult:
    """Result of dispatching a sub-agent through an IDE adapter.

    `output`        : the agent's stdout / response text
    `exit_code`     : 0 = success; non-zero = failure
    `duration_ms`   : wall-clock ms from dispatch to result
    `agent_type`    : the agent_name that was dispatched (echoed back for trace)
    `error`         : optional error message (None on success)
    """

    output: str
    exit_code: int
    duration_ms: int
    agent_type: str
    error: str | None = None


@runtime_checkable
class IDEAdapter(Protocol):
    """Adapter for an AI IDE/agent platform.

    Each platform (claude-code / cursor / vscode-codex / codex-cli / inline)
    implements this Protocol. arcgentic skills + CLI invoke platform-agnostic
    methods; the adapter translates to platform-specific tool calls.

    Anti-contamination invariant (spec § 1.5): adapter methods MUST NOT inject
    `tools=` or `tool_choice=` at the agent level. Those belong one layer down
    in the LLM-client layer.
    """

    platform_name: str  # "claude-code" / "cursor" / "vscode-codex" / "codex-cli" / "inline"

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: str | None = None,  # "worktree" or None
    ) -> AgentDispatchResult:
        """Dispatch a sub-agent.

        `agent_name` maps to a markdown file at agents/<name>.md.
        `prompt` is the full self-contained brief; agent has zero session context.
        Returns the agent's response wrapped in AgentDispatchResult.
        """
        ...

    def invoke_skill(self, skill_name: str, args: str = "") -> str:
        """Invoke an arcgentic skill in-process.

        `skill_name` maps to a markdown file at skills/<name>/SKILL.md.
        `args` is the optional argument string for the skill.
        Returns the skill's textual output.
        """
        ...

    def read_file(self, path: str) -> str: ...

    def write_file(self, path: str, content: str) -> None: ...

    def edit_file(self, path: str, old: str, new: str) -> None: ...

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        """Run a shell command; return (output, exit_code)."""
        ...

    def git_diff_staged(self) -> str: ...

    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        """Stage given files (or all staged if None) and commit. Returns commit SHA."""
        ...
