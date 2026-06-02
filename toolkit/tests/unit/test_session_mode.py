from __future__ import annotations

from arcgentic.session_mode import (
    ModeChoiceError,
    SessionModeInput,
    generate_identity_prompts,
    recommend_session_mode,
    validate_mode_choice,
)


def test_recommends_multi_session_for_workflow_release_round() -> None:
    result = recommend_session_mode(
        SessionModeInput(
            round_id="R1-v1-openspec-marketplace",
            task_count=8,
            expected_duration_hours=18,
            touched_surfaces=18,
            risk_flags=("workflow-contract", "release-gate", "cross-role"),
            dispatch_available=False,
            candidate_roles=("minimal-change engineer", "software architect"),
        )
    )

    assert result.recommended_mode == "multi-session"
    assert result.requires_user_confirmation is True
    assert any("dispatch transport unavailable" in reason for reason in result.reasons)
    assert "developer" in result.identity_prompts


def test_recommends_single_session_for_small_local_change() -> None:
    result = recommend_session_mode(
        SessionModeInput(
            round_id="R-small",
            task_count=1,
            expected_duration_hours=1,
            touched_surfaces=2,
            risk_flags=(),
            dispatch_available=True,
            candidate_roles=("developer",),
        )
    )

    assert result.recommended_mode == "single-session"
    assert result.confidence >= 0.7


def test_refuses_single_session_auto_audit_without_dispatch() -> None:
    try:
        validate_mode_choice("single-session", dispatch_available=False, auto_audit=True)
    except ModeChoiceError as exc:
        assert "dispatch transport" in str(exc)
    else:
        raise AssertionError("expected ModeChoiceError")


def test_generates_both_identity_handoff_prompts() -> None:
    prompts = generate_identity_prompts(
        round_id="R1",
        handoff_path="docs/superpowers/plans/R1.md",
        candidate_roles=("developer", "auditor"),
    )

    assert "developer only" in prompts["developer"]
    assert "auditor only" in prompts["auditor"]
    assert "docs/superpowers/plans/R1.md" in prompts["developer"]
