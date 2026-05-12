"""Tests for detect_adapter() in arcgentic.adapters.

TDD: this file is written before __init__.py has detect_adapter().
Run order:
  1. pytest tests/unit/adapters/test_detect.py  → FAIL (ImportError / AttributeError)
  2. implement detect_adapter() in adapters/__init__.py
  3. pytest tests/unit/adapters/test_detect.py  → PASS (10 tests)

All tests are hermetic: every test clears the 4 env vars that detect_adapter()
inspects and patches both `_has_dir` and `which` to known values so the result
never depends on the developer's actual environment.

Detection priority (first match wins):
  1. Claude Code  — CLAUDE_CODE_SESSION env OR ~/.claude/skills dir
  2. Cursor       — CURSOR_SESSION env OR .cursor/rules dir
  3. VSCode+Codex — VSCODE_PID env AND `codex` binary on PATH
  4. Codex CLI    — CODEX_SESSION env OR `codex` binary on PATH (no VSCODE_PID)
  5. Inline       — fallback

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 3.6
"""

from __future__ import annotations

import pytest

from arcgentic.adapters import detect_adapter
from arcgentic.adapters.base import IDEAdapter
from arcgentic.adapters.claude_code import ClaudeCodeAdapter
from arcgentic.adapters.codex_cli import CodexCLIAdapter
from arcgentic.adapters.cursor import CursorAdapter
from arcgentic.adapters.inline import InlineAdapter
from arcgentic.adapters.vscode_codex import VSCodeCodexAdapter

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ALL_ENVS = ("CLAUDE_CODE_SESSION", "CURSOR_SESSION", "VSCODE_PID", "CODEX_SESSION")


def _clear_all_envs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every env var detect_adapter() inspects, so tests start hermetic."""
    for var in _ALL_ENVS:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# Test 1: Claude Code detected via CLAUDE_CODE_SESSION env var
# ---------------------------------------------------------------------------


def test_detect_claude_code_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLAUDE_CODE_SESSION=1 → ClaudeCodeAdapter, even if _has_dir and which return nothing."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_SESSION", "1")
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, ClaudeCodeAdapter)
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 2: Claude Code detected via ~/.claude/skills directory marker
# ---------------------------------------------------------------------------


def test_detect_claude_code_via_skills_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """~/.claude/skills exists (and no env var) → ClaudeCodeAdapter."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setattr(
        "arcgentic.adapters._has_dir",
        lambda p: p == "~/.claude/skills",
    )
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, ClaudeCodeAdapter)


# ---------------------------------------------------------------------------
# Test 3: Cursor detected via CURSOR_SESSION env var
# ---------------------------------------------------------------------------


def test_detect_cursor_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CURSOR_SESSION=1 → CursorAdapter (claude markers absent)."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setenv("CURSOR_SESSION", "1")
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, CursorAdapter)
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 4: Cursor detected via .cursor/rules directory marker
# ---------------------------------------------------------------------------


def test_detect_cursor_via_rules_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """.cursor/rules dir exists (no env vars, no claude marker) → CursorAdapter."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setattr(
        "arcgentic.adapters._has_dir",
        lambda p: p == ".cursor/rules",
    )
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, CursorAdapter)


# ---------------------------------------------------------------------------
# Test 5: VSCode + Codex detected via VSCODE_PID env AND codex binary
# ---------------------------------------------------------------------------


def test_detect_vscode_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    """VSCODE_PID set AND `codex` on PATH → VSCodeCodexAdapter."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setenv("VSCODE_PID", "1234")
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr(
        "arcgentic.adapters.which",
        lambda cmd: "/usr/bin/codex" if cmd == "codex" else None,
    )

    adapter = detect_adapter()

    assert isinstance(adapter, VSCodeCodexAdapter)
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 6: Codex CLI detected via CODEX_SESSION env var
# ---------------------------------------------------------------------------


def test_detect_codex_cli_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CODEX_SESSION=1 (no VSCODE_PID) → CodexCLIAdapter."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setenv("CODEX_SESSION", "1")
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    # which returning something exercises a different code path; make it truthy
    # so we know CODEX_SESSION (not binary) fires
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, CodexCLIAdapter)
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 7: Codex CLI detected via codex binary only (no env vars)
# ---------------------------------------------------------------------------


def test_detect_codex_cli_via_binary_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """`codex` on PATH but NO env vars → CodexCLIAdapter (not VSCodeCodexAdapter)."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr(
        "arcgentic.adapters.which",
        lambda cmd: "/usr/bin/codex" if cmd == "codex" else None,
    )
    # Crucially: VSCODE_PID is NOT set, so rule 3 (VSCode+Codex) does NOT fire.

    adapter = detect_adapter()

    assert isinstance(adapter, CodexCLIAdapter)


# ---------------------------------------------------------------------------
# Test 8: Inline fallback — nothing detected
# ---------------------------------------------------------------------------


def test_detect_fallback_to_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env vars, no fs markers, no codex binary → InlineAdapter."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, InlineAdapter)
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 9: Priority — Claude Code wins over Cursor when BOTH env vars set
# ---------------------------------------------------------------------------


def test_priority_claude_over_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLAUDE_CODE_SESSION + CURSOR_SESSION both set → ClaudeCodeAdapter wins."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_SESSION", "1")
    monkeypatch.setenv("CURSOR_SESSION", "1")
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr("arcgentic.adapters.which", lambda _: None)

    adapter = detect_adapter()

    assert isinstance(adapter, ClaudeCodeAdapter)
    assert not isinstance(adapter, CursorAdapter)


# ---------------------------------------------------------------------------
# Test 10: Priority — VSCode+Codex wins over Codex-CLI when VSCODE_PID set
# ---------------------------------------------------------------------------


def test_priority_vscode_codex_over_codex_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """VSCODE_PID + CODEX_SESSION + codex binary → VSCodeCodexAdapter (rule 3 before rule 4)."""
    _clear_all_envs(monkeypatch)
    monkeypatch.setenv("VSCODE_PID", "5678")
    monkeypatch.setenv("CODEX_SESSION", "1")
    monkeypatch.setattr("arcgentic.adapters._has_dir", lambda _: False)
    monkeypatch.setattr(
        "arcgentic.adapters.which",
        lambda cmd: "/usr/bin/codex" if cmd == "codex" else None,
    )

    adapter = detect_adapter()

    assert isinstance(adapter, VSCodeCodexAdapter)
    assert not isinstance(adapter, CodexCLIAdapter)
