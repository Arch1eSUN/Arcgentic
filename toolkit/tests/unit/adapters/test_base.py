"""Tests for arcgentic.adapters.base — IDEAdapter Protocol + AgentDispatchResult.

TDD: this file is written before base.py exists.
Run order:
  1. pytest tests/unit/adapters/test_base.py  → FAIL (ImportError)
  2. create base.py
  3. pytest tests/unit/adapters/test_base.py  → PASS (5 tests)
"""

from __future__ import annotations

import pytest

from arcgentic.adapters.base import AgentDispatchResult, IDEAdapter

# ---------------------------------------------------------------------------
# Test 1: AgentDispatchResult constructible with required fields only
# ---------------------------------------------------------------------------


def test_agent_dispatch_result_required_fields() -> None:
    """AgentDispatchResult builds with the four required fields; error defaults to None."""
    result = AgentDispatchResult(
        output="hello",
        exit_code=0,
        duration_ms=42,
        agent_type="auditor",
    )
    assert result.output == "hello"
    assert result.exit_code == 0
    assert result.duration_ms == 42
    assert result.agent_type == "auditor"
    assert result.error is None


# ---------------------------------------------------------------------------
# Test 2: AgentDispatchResult is frozen (immutable)
# ---------------------------------------------------------------------------


def test_agent_dispatch_result_is_frozen() -> None:
    """Assigning to any field on a frozen dataclass must raise an error."""
    result = AgentDispatchResult(
        output="x",
        exit_code=1,
        duration_ms=10,
        agent_type="developer",
        error="something went wrong",
    )
    with pytest.raises((AttributeError, TypeError)):
        result.output = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test 3: IDEAdapter is runtime_checkable — a fully duck-typed class IS accepted
# ---------------------------------------------------------------------------


class _FullAdapter:
    """A minimal valid IDEAdapter implementation used in positive conformance tests."""

    platform_name: str = "inline"

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: str | None = None,
    ) -> AgentDispatchResult:
        return AgentDispatchResult(
            output="",
            exit_code=0,
            duration_ms=0,
            agent_type=agent_name,
        )

    def invoke_skill(self, skill_name: str, args: str = "") -> str:
        return ""

    def read_file(self, path: str) -> str:
        return ""

    def write_file(self, path: str, content: str) -> None:
        pass

    def edit_file(self, path: str, old: str, new: str) -> None:
        pass

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        return ("", 0)

    def git_diff_staged(self) -> str:
        return ""

    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        return "abc123"


def test_ide_adapter_runtime_check_positive() -> None:
    """An object implementing all 9 methods + platform_name passes isinstance check."""
    adapter = _FullAdapter()
    assert isinstance(adapter, IDEAdapter), (
        "A fully duck-typed adapter must be recognized by runtime_checkable isinstance"
    )


# ---------------------------------------------------------------------------
# Test 4: IDEAdapter rejects an incomplete object (missing dispatch_agent)
# ---------------------------------------------------------------------------


class _IncompleteAdapter:
    """Adapter missing dispatch_agent — must fail isinstance check."""

    platform_name: str = "broken"

    def invoke_skill(self, skill_name: str, args: str = "") -> str:
        return ""

    def read_file(self, path: str) -> str:
        return ""

    def write_file(self, path: str, content: str) -> None:
        pass

    def edit_file(self, path: str, old: str, new: str) -> None:
        pass

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        return ("", 0)

    def git_diff_staged(self) -> str:
        return ""

    def git_commit(self, message: str, files: list[str] | None = None) -> str:
        return ""


def test_ide_adapter_runtime_check_negative() -> None:
    """An object missing dispatch_agent must NOT satisfy isinstance(obj, IDEAdapter)."""
    incomplete = _IncompleteAdapter()
    assert not isinstance(incomplete, IDEAdapter), (
        "An adapter missing dispatch_agent must be rejected by isinstance"
    )


# ---------------------------------------------------------------------------
# Test 5: AgentDispatchResult with explicit error field
# ---------------------------------------------------------------------------


def test_agent_dispatch_result_with_error() -> None:
    """AgentDispatchResult stores the optional error field correctly."""
    result = AgentDispatchResult(
        output="",
        exit_code=2,
        duration_ms=500,
        agent_type="planner",
        error="timeout exceeded",
    )
    assert result.exit_code == 2
    assert result.error == "timeout exceeded"
