"""Tests for arcgentic.adapters.inline — InlineAdapter.

TDD: this file is written before inline.py exists.
Run order:
  1. pytest tests/unit/adapters/test_inline.py  → FAIL (ImportError)
  2. create inline.py
  3. pytest tests/unit/adapters/test_inline.py  → PASS

InlineAdapter is the fallback for environments without an LLM host.
- dispatch_agent: returns prompt unchanged with exit_code=0 + warning log
- invoke_skill: returns "" + warning log
- filesystem/git: delegates to _local_env
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from arcgentic.adapters.base import IDEAdapter
from arcgentic.adapters.inline import InlineAdapter

# ---------------------------------------------------------------------------
# Test 1: platform_name
# ---------------------------------------------------------------------------


def test_platform_name() -> None:
    """InlineAdapter.platform_name must equal 'inline'."""
    adapter = InlineAdapter()
    assert adapter.platform_name == "inline"


# ---------------------------------------------------------------------------
# Test 2: Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_conformance() -> None:
    """InlineAdapter must satisfy isinstance(adapter, IDEAdapter)."""
    adapter = InlineAdapter()
    assert isinstance(adapter, IDEAdapter)


# ---------------------------------------------------------------------------
# Test 3: dispatch_agent returns prompt unchanged with exit_code=0
# ---------------------------------------------------------------------------


def test_dispatch_agent_returns_prompt_unchanged() -> None:
    """dispatch_agent returns the prompt as output with exit_code=0."""
    adapter = InlineAdapter()
    prompt = "Do this audit task: verify spec compliance."
    result = adapter.dispatch_agent("auditor", prompt)

    assert result.output == prompt
    assert result.exit_code == 0
    assert result.error is None
    assert result.agent_type == "auditor"
    assert result.duration_ms == 0


# ---------------------------------------------------------------------------
# Test 4: dispatch_agent logs a warning
# ---------------------------------------------------------------------------


def test_dispatch_agent_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """dispatch_agent emits a WARNING log about no LLM host."""
    adapter = InlineAdapter()
    with caplog.at_level(logging.WARNING, logger="arcgentic.adapters.inline"):
        adapter.dispatch_agent("planner", "plan the round")

    assert len(caplog.records) >= 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    msg = record.message.lower()
    assert "inline" in msg or "no llm" in msg or "dispatch" in msg


# ---------------------------------------------------------------------------
# Test 5: dispatch_agent with different agent_name
# ---------------------------------------------------------------------------


def test_dispatch_agent_preserves_agent_type() -> None:
    """dispatch_agent echoes agent_type correctly for any agent_name."""
    adapter = InlineAdapter()
    result = adapter.dispatch_agent("developer", "implement feature X")
    assert result.agent_type == "developer"
    assert result.output == "implement feature X"


# ---------------------------------------------------------------------------
# Test 6: invoke_skill returns empty string
# ---------------------------------------------------------------------------


def test_invoke_skill_returns_empty_string() -> None:
    """invoke_skill returns '' when no LLM host available."""
    adapter = InlineAdapter()
    output = adapter.invoke_skill("pre-round-scan")
    assert output == ""


def test_invoke_skill_with_args_returns_empty_string() -> None:
    """invoke_skill with args returns '' (args are ignored)."""
    adapter = InlineAdapter()
    output = adapter.invoke_skill("audit-round", "some args here")
    assert output == ""


# ---------------------------------------------------------------------------
# Test 7: invoke_skill logs a warning
# ---------------------------------------------------------------------------


def test_invoke_skill_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """invoke_skill emits a WARNING log about no LLM host."""
    adapter = InlineAdapter()
    with caplog.at_level(logging.WARNING, logger="arcgentic.adapters.inline"):
        adapter.invoke_skill("verify-gates")

    assert len(caplog.records) >= 1
    assert caplog.records[0].levelno == logging.WARNING


# ---------------------------------------------------------------------------
# Tests 8-10: filesystem delegation to _local_env
# ---------------------------------------------------------------------------


def test_read_file_delegates(tmp_path: Path) -> None:
    """read_file delegates to _local_env.read_file."""
    target = tmp_path / "r.txt"
    target.write_text("inline read", encoding="utf-8")
    adapter = InlineAdapter()
    assert adapter.read_file(str(target)) == "inline read"


def test_write_file_delegates(tmp_path: Path) -> None:
    """write_file delegates to _local_env.write_file."""
    target = tmp_path / "w.txt"
    adapter = InlineAdapter()
    adapter.write_file(str(target), "inline write")
    assert target.read_text(encoding="utf-8") == "inline write"


def test_shell_delegates() -> None:
    """shell delegates to _local_env.shell (real subprocess)."""
    adapter = InlineAdapter()
    output, code = adapter.shell("echo inline shell")
    assert code == 0
    assert "inline shell" in output
