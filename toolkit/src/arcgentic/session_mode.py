"""Session-mode recommendation and identity prompt generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Mode = Literal["single-session", "multi-session"]


class ModeChoiceError(ValueError):
    """Raised when a requested session mode violates mechanical constraints."""


@dataclass(frozen=True)
class SessionModeInput:
    """Inputs the orchestrator knows before developer work starts."""

    round_id: str
    task_count: int
    expected_duration_hours: int
    touched_surfaces: int
    risk_flags: tuple[str, ...]
    dispatch_available: bool
    candidate_roles: tuple[str, ...]
    handoff_path: str = ""


@dataclass(frozen=True)
class SessionModeRecommendation:
    """Decision object shown before asking the user to choose a mode."""

    recommended_mode: Mode
    confidence: float
    reasons: tuple[str, ...]
    candidate_roles: tuple[str, ...]
    requires_user_confirmation: bool
    identity_prompts: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_HIGH_RISK_KEYWORDS = (
    "workflow",
    "release",
    "security",
    "cross-role",
    "external",
    "manifest",
    "package",
    "schema",
)


def recommend_session_mode(inputs: SessionModeInput) -> SessionModeRecommendation:
    """Recommend single-session or multi-session from handoff risk signals."""

    reasons: list[str] = []
    high_risk = [
        flag
        for flag in inputs.risk_flags
        if any(keyword in flag for keyword in _HIGH_RISK_KEYWORDS)
    ]
    if high_risk:
        reasons.append("risk flags require role separation: " + ", ".join(high_risk))
    if inputs.expected_duration_hours >= 8:
        reasons.append("expected duration spans a large implementation block")
    if inputs.task_count >= 4:
        reasons.append("multiple implementation tasks need checkpointable verification")
    if inputs.touched_surfaces >= 10:
        reasons.append("large touched surface increases audit contamination risk")
    if not inputs.dispatch_available:
        reasons.append("dispatch transport unavailable or unverified")

    if reasons:
        mode: Mode = "multi-session"
        confidence = 0.9 if len(reasons) >= 3 else 0.78
    else:
        mode = "single-session"
        confidence = 0.74
        reasons.append("short low-risk local change with verified dispatch")

    prompts = generate_identity_prompts(
        round_id=inputs.round_id,
        handoff_path=inputs.handoff_path,
        candidate_roles=inputs.candidate_roles,
    )
    return SessionModeRecommendation(
        recommended_mode=mode,
        confidence=confidence,
        reasons=tuple(reasons),
        candidate_roles=inputs.candidate_roles,
        requires_user_confirmation=True,
        identity_prompts=prompts,
    )


def validate_mode_choice(mode: Mode, *, dispatch_available: bool, auto_audit: bool) -> None:
    """Reject choices that would claim automation without real dispatch transport."""

    if mode == "single-session" and auto_audit and not dispatch_available:
        raise ModeChoiceError(
            "single-session auto-audit requires verified dispatch transport; choose multi-session"
        )


def generate_identity_prompts(
    *,
    round_id: str,
    handoff_path: str,
    candidate_roles: tuple[str, ...],
) -> dict[str, str]:
    """Generate developer and auditor prompts for multi-session handoff."""

    roles = ", ".join(candidate_roles) if candidate_roles else "developer, auditor"
    developer = (
        f"You are the arcgentic developer only for round {round_id}.\n"
        f"Read {handoff_path or '<handoff-path>'} and .agentic-rounds/state.yaml.\n"
        "Implement the handoff scope, write self-audit, record dev commits, "
        "then stop at awaiting_audit. Do not write the external audit verdict.\n"
        f"Suggested role families: {roles}."
    )
    auditor = (
        f"You are the arcgentic auditor only for round {round_id}.\n"
        f"Read {handoff_path or '<handoff-path>'}, the final self-audit, and dev commits.\n"
        "Independently re-run mechanical facts and write PASS or NEEDS_FIX only."
    )
    return {"developer": developer, "auditor": auditor}


def input_from_handoff(
    *,
    round_id: str,
    handoff_text: str,
    handoff_path: str,
    dispatch_available: bool,
) -> SessionModeInput:
    """Derive conservative classifier inputs from a markdown handoff."""

    lower = handoff_text.lower()
    risk_flags = tuple(keyword for keyword in _HIGH_RISK_KEYWORDS if keyword in lower)
    task_count = lower.count("implementation task")
    touched_surfaces = sum(
        1
        for marker in (
            "source-intake",
            "capability-registry",
            "spec-governance",
            "agency-roster",
            "session-mode",
            "release-readiness",
            "cli",
            "readme",
        )
        if marker in lower
    )
    expected_duration = 18 if "multi-session" in lower or "release" in lower else 2
    return SessionModeInput(
        round_id=round_id,
        task_count=max(task_count, 1),
        expected_duration_hours=expected_duration,
        touched_surfaces=touched_surfaces,
        risk_flags=risk_flags,
        dispatch_available=dispatch_available,
        candidate_roles=("minimal-change engineer", "software architect", "auditor"),
        handoff_path=handoff_path,
    )
