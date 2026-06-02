"""Orchestrator dispatch order for multi-session arcgentic rounds."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .session_mode import Mode, generate_identity_prompts


@dataclass(frozen=True)
class DispatchStep:
    role: str
    prompt: str
    stop_condition: str
    return_signal: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class DispatchOrder:
    mode: Mode
    steps: tuple[DispatchStep, ...]

    def to_dict(self) -> dict[str, object]:
        return {"mode": self.mode, "steps": [step.to_dict() for step in self.steps]}


def build_dispatch_order(*, round_id: str, handoff_path: Path, mode: Mode) -> DispatchOrder:
    """Build the deterministic next-session order for an inherited project mode."""

    prompts = generate_identity_prompts(
        round_id=round_id,
        handoff_path=str(handoff_path),
        candidate_roles=("workflow engineer", "test engineer"),
    )
    if mode == "single-session":
        return DispatchOrder(
            mode=mode,
            steps=(
                DispatchStep(
                    role="orchestrator",
                    prompt="Run planner, developer, auditor, and closeout in one verified session.",
                    stop_condition="round reaches closed or needs_fix",
                    return_signal="state = closed or needs_fix",
                ),
            ),
        )
    return DispatchOrder(
        mode=mode,
        steps=(
            DispatchStep(
                role="developer",
                prompt=prompts["developer"],
                stop_condition=(
                    "implementation complete, self-audit written, state = awaiting_audit"
                ),
                return_signal="state = awaiting_audit with dev_commits and self_audit_doc",
            ),
            DispatchStep(
                role="auditor",
                prompt=prompts["auditor"],
                stop_condition="external verdict written and state = passed or needs_fix",
                return_signal="state = passed or needs_fix with audit_verdict",
            ),
            DispatchStep(
                role="closeout",
                prompt=prompts["closeout"],
                stop_condition="passed round is closed and next-round recommendation emitted",
                return_signal="state = closed with last_passed_round anchored",
            ),
        ),
    )
