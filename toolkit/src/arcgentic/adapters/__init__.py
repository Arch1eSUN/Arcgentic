"""IDE adapter auto-detection.

`detect_adapter()` inspects environment variables, filesystem markers, and
binary availability to select the appropriate adapter for the current host.
Falls back to InlineAdapter if no LLM host can be confidently identified.

Detection priority (first match wins):
  1. Claude Code  — env CLAUDE_CODE_SESSION OR ~/.claude/skills exists
  2. Cursor       — env CURSOR_SESSION OR .cursor/rules directory in CWD
  3. VSCode+Codex — env VSCODE_PID present AND `codex` binary on PATH
  4. Codex CLI    — env CODEX_SESSION OR `codex` binary on PATH (without VSCODE_PID)
  5. Inline       — fallback; no LLM host

Public API:
  detect_adapter() -> IDEAdapter
  IDEAdapter (re-export from .base for convenience)
  AgentDispatchResult (re-export from .base)

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.6
"""

from __future__ import annotations

import os
from pathlib import Path
from shutil import which

from .base import AgentDispatchResult, IDEAdapter

__all__ = ["detect_adapter", "IDEAdapter", "AgentDispatchResult"]


def detect_adapter() -> IDEAdapter:
    """Return the IDEAdapter best matching the current runtime environment.

    Falls back to InlineAdapter if no LLM host can be detected. Callers should
    NOT assume the returned adapter can dispatch agents (InlineAdapter can't
    actually dispatch — it's a degraded fallback for dry-run / headless use).
    """
    # 1. Claude Code
    if os.environ.get("CLAUDE_CODE_SESSION") or _has_dir("~/.claude/skills"):
        from .claude_code import ClaudeCodeAdapter
        return ClaudeCodeAdapter()

    # 2. Cursor
    if os.environ.get("CURSOR_SESSION") or _has_dir(".cursor/rules"):
        from .cursor import CursorAdapter
        return CursorAdapter()

    # 3. VSCode + Codex (must have BOTH a VSCode env marker AND codex binary)
    if os.environ.get("VSCODE_PID") and which("codex"):
        from .vscode_codex import VSCodeCodexAdapter
        return VSCodeCodexAdapter()

    # 4. Codex CLI standalone (CODEX_SESSION env, OR codex binary without VSCode)
    if os.environ.get("CODEX_SESSION") or which("codex"):
        from .codex_cli import CodexCLIAdapter
        return CodexCLIAdapter()

    # 5. Fallback
    from .inline import InlineAdapter
    return InlineAdapter()


def _has_dir(path: str) -> bool:
    """Return True if `path` (with ~ expansion) is a directory."""
    return Path(path).expanduser().is_dir()
