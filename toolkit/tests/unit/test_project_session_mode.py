from __future__ import annotations

from pathlib import Path

from arcgentic.orchestrator_dispatch import build_dispatch_order
from arcgentic.session_mode import (
    ProjectSessionModeError,
    generate_identity_prompts,
    project_mode_from_state,
    should_request_session_mode,
)


def test_project_level_session_mode_is_read_once_and_inherited() -> None:
    state = {
        "project": {"session_mode": {"mode": "multi-session", "decided_at_round": "R1"}},
        "current_round": {"id": "R2-v1-release-hardening"},
    }

    mode = project_mode_from_state(state)

    assert mode.mode == "multi-session"
    assert mode.decided_at_round == "R1"
    assert should_request_session_mode(state, "R2-v1-release-hardening") is False


def test_missing_project_mode_requests_choice() -> None:
    state: dict[str, object] = {"project": {}, "current_round": {"id": "R2"}}

    assert should_request_session_mode(state, "R2") is True


def test_invalid_project_mode_fails_closed() -> None:
    state: dict[str, object] = {"project": {"session_mode": {"mode": "team-vibes"}}}

    try:
        project_mode_from_state(state)
    except ProjectSessionModeError as exc:
        assert "unsupported project session mode" in str(exc)
    else:
        raise AssertionError("expected ProjectSessionModeError")


def test_role_specific_prompts_are_distinct() -> None:
    prompts = generate_identity_prompts(
        round_id="R2",
        handoff_path="docs/superpowers/plans/R2.md",
        candidate_roles=("workflow engineer",),
    )

    assert "developer only" in prompts["developer"]
    assert "auditor only" in prompts["auditor"]
    assert "closeout only" in prompts["closeout"]
    assert len({prompts["developer"], prompts["auditor"], prompts["closeout"]}) == 3


def test_dispatch_order_contains_prompt_stop_condition_and_return_signal() -> None:
    dispatch = build_dispatch_order(
        round_id="R2",
        handoff_path=Path("docs/superpowers/plans/R2.md"),
        mode="multi-session",
    )

    assert [step.role for step in dispatch.steps] == ["developer", "auditor", "closeout"]
    assert "awaiting_audit" in dispatch.steps[0].stop_condition
    assert "state = passed or needs_fix" in dispatch.steps[1].return_signal
    assert "closed" in dispatch.steps[2].stop_condition
