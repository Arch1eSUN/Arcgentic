"""plan-round skill implementation.

Public entry point:
    run(round_name, round_type, prior_round_anchor, scope_description) -> RunResult

Algorithm (per spec § 4.1.3):
1. Validate inputs (round_name regex, prior_round_anchor 40-char SHA, round_type enum)
2. Compute template_size from round_type
3. Read prior-round context (best-effort; missing prior round is non-fatal for the very first round)
4. Build self-contained planner brief
5. Dispatch planner agent via detect_adapter()
6. Validate planner output (section count, MUST sections, no TBD/TODO/XXX)
7. Write handoff to docs/superpowers/plans/{YYYY-MM-DD}-{round_name}-handoff.md
8. Return RunResult

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 4.1
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from arcgentic.adapters import IDEAdapter, detect_adapter

# ── Constants ──────────────────────────────────────────────────────────

_ROUND_NAME_PATTERN = re.compile(r"^R\d+(\.\d+(\.\d+)?|-[A-Za-z][\w-]*)?$")
_FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_ROUND_TYPE_TO_TEMPLATE_SIZE: dict[str, int] = {
    "substrate-touching": 18,
    "fix-round": 12,
    "entry-admin": 10,
    "close-admin": 10,
    # v0.2.0 P0: all admin types use 10-section (8-section deferred to v0.3+)
    "meta-admin-sweep": 10,
}

# Maps round_type to the spec section that defines its handoff template structure.
# Used in planner briefs so the agent can reference the canonical spec section.
_ROUND_TYPE_TO_SPEC_SECTION: dict[str, str] = {
    "substrate-touching": "7.1",
    "fix-round": "7.2",
    "entry-admin": "7.3",
    "close-admin": "7.3",
    "meta-admin-sweep": "7.3",
}

_MUST_SECTION_MIN_LENGTH = 50  # chars — per planner agent's quality bar


# ── Result type ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RunResult:
    """Result of running plan_round.

    Attributes:
        handoff_path: Path where the handoff doc was written (None on validation failure).
        section_count: Number of `## ` sections produced.
        loc: Total line count of the handoff.
        warnings: Any non-fatal issues during planner output validation.
        exit_code: 0 = success; 1 = validation failed; 2 = input error.
        error: Optional error message on failure.
    """

    handoff_path: Path | None
    section_count: int
    loc: int
    warnings: list[str] = field(default_factory=list)
    exit_code: int = 0
    error: str | None = None

    def summary(self) -> str:
        if self.error:
            return f"FAILED: {self.error}"
        lines = [f"plan-round succeeded: wrote {self.handoff_path}"]
        lines.append(f"  section_count: {self.section_count}")
        lines.append(f"  loc: {self.loc}")
        if self.warnings:
            lines.append(f"  warnings: {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)


# ── Errors ─────────────────────────────────────────────────────────────

class PlanRoundError(Exception):
    """Raised for input-validation failures + planner-output validation failures."""


# ── Helpers ────────────────────────────────────────────────────────────

def _validate_inputs(round_name: str, round_type: str, prior_round_anchor: str) -> None:
    if not _ROUND_NAME_PATTERN.match(round_name):
        raise PlanRoundError(
            f"Invalid round_name: {round_name!r}. "
            "Expected R<phase>[.<round>[.<fix>]] or R<phase>-<name>."
        )
    if round_type not in _ROUND_TYPE_TO_TEMPLATE_SIZE:
        raise PlanRoundError(
            f"Invalid round_type: {round_type!r}. Must be one of "
            f"{sorted(_ROUND_TYPE_TO_TEMPLATE_SIZE.keys())}."
        )
    if not _FULL_SHA_PATTERN.match(prior_round_anchor):
        raise PlanRoundError(
            f"Invalid prior_round_anchor: {prior_round_anchor!r}. Must be a full 40-char hex SHA."
        )


def _template_size_label(round_type: str) -> str:
    size = _ROUND_TYPE_TO_TEMPLATE_SIZE[round_type]
    if size == 18:
        return "full"
    if size == 12:
        return "narrow"
    return "admin"


def _build_planner_brief(
    round_name: str,
    round_type: str,
    prior_round_anchor: str,
    scope_description: str,
    template_size_label: str,
    prior_handoff_summary: str,
) -> str:
    """Build the self-contained brief passed to the planner agent (per b.1 contract)."""
    return f"""CONTEXT (self-contained):
- Round name: {round_name}
- Round type: {round_type}
- Prior round anchor: {prior_round_anchor}
- Scope description: {scope_description or "(scope to be filled in handoff § 1)"}
- Template size: {template_size_label}

PRIOR ROUND CONTEXT:
{prior_handoff_summary or "(no prior round handoff found; treat as first round in phase)"}

TASK:
Generate a complete handoff doc for {round_name} using the {template_size_label} template
({_ROUND_TYPE_TO_TEMPLATE_SIZE[round_type]} sections).

REQUIRED SECTIONS: exactly {_ROUND_TYPE_TO_TEMPLATE_SIZE[round_type]} numbered `## ` sections \
(per spec § {_ROUND_TYPE_TO_SPEC_SECTION[round_type]} template structure).

QUALITY BAR:
- No `TBD` / `TODO` / `XXX` / `(fill in)` markers in MUST sections
- At least 1 reference row with 4-column triplet in § 2 (reference scan)
- Concrete file paths (not "various files") in § 5 commit plans
- audit fact-shape targets in § 12 enumerate 25-40 facts
- Section count exactly {_ROUND_TYPE_TO_TEMPLATE_SIZE[round_type]}

OUTPUT:
The complete handoff doc as markdown. Start with `# {round_name} — ...` and end with the
final `*<type> handoff written by planner agent (arcgentic vX.Y.Z).*` line.
"""


def _discover_repo_root(adapter: IDEAdapter) -> Path:
    """Return the git repo root path, or CWD if not in a git repo."""
    try:
        stdout, code = adapter.shell("git rev-parse --show-toplevel")
        if code == 0 and stdout.strip():
            return Path(stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def _read_prior_handoff(adapter: IDEAdapter, prior_anchor: str, repo_root: Path) -> str:
    """Best-effort read of prior-round handoff. Returns summary string (empty on miss).

    In v0.2.0 P0 this is a stub: searches docs/superpowers/plans/ for any file containing
    the anchor SHA. Future versions may use git log + structured parsing.
    """
    plans_dir = repo_root / "docs/superpowers/plans"
    if not plans_dir.is_dir():
        return ""
    for p in sorted(plans_dir.glob("*.md"), reverse=True):
        try:
            content = adapter.read_file(str(p))
            if prior_anchor in content:
                # Found prior handoff containing this anchor; return a summary line.
                return f"Prior handoff at {p.name} (matched anchor {prior_anchor[:12]}...)"
        except OSError:
            continue
    return ""


def _validate_planner_output(output: str, expected_sections: int) -> tuple[list[str], int, int]:
    """Validate planner output. Returns (warnings, section_count, loc).

    Section counting skips fenced code blocks (lines between ``` markers) so embedded
    code with `##` comments doesn't inflate the count.

    Raises PlanRoundError on hard failures (section count mismatch).
    Adds non-fatal warnings to the list (e.g. TBD/TODO markers in MUST sections).
    """
    warnings: list[str] = []
    lines = output.splitlines()
    loc = len(lines)

    section_count = 0
    in_fence = False
    for ln in lines:
        stripped = ln.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if ln.startswith("## "):
            section_count += 1

    if section_count != expected_sections:
        raise PlanRoundError(
            f"Planner output has {section_count} sections; expected exactly {expected_sections}."
        )

    # Check for TBD/TODO/XXX markers (non-fatal warnings — planner self-check should catch these)
    for marker in ("TBD", "TODO", "XXX", "(fill in)"):
        if marker in output:
            warnings.append(
                f"Output contains `{marker}` marker — planner agent's self-check missed it"
            )

    return warnings, section_count, loc


def _handoff_path(round_name: str, repo_root: Path) -> Path:
    """Compute the handoff file path under repo_root."""
    today = date.today().isoformat()  # YYYY-MM-DD
    return repo_root / "docs/superpowers/plans" / f"{today}-{round_name}-handoff.md"


# ── Public entry point ─────────────────────────────────────────────────

def run(
    *,
    round_name: str,
    round_type: str,
    prior_round_anchor: str,
    scope_description: str = "",
    adapter: IDEAdapter | None = None,
    repo_root: Path | None = None,
) -> RunResult:
    """Generate a complete round handoff doc.

    `adapter` defaults to detect_adapter() — tests can inject InlineAdapter or a mock.
    `repo_root` defaults to discovery via `git rev-parse --show-toplevel`. Tests should
    explicitly pass repo_root=tmp_path to isolate filesystem operations.

    Exit code semantics:
    - 0: success (handoff written). Non-fatal warnings (e.g. TBD/TODO markers in MUST sections)
      populate `RunResult.warnings` but do not change exit_code.
    - 1: validation failure (planner output had wrong section count, or dispatch failed).
    - 2: input validation failure (bad round_name / SHA / round_type).
    """
    try:
        _validate_inputs(round_name, round_type, prior_round_anchor)
    except PlanRoundError as e:
        return RunResult(
            handoff_path=None,
            section_count=0,
            loc=0,
            warnings=[],
            exit_code=2,
            error=str(e),
        )

    resolved_adapter: IDEAdapter = adapter if adapter is not None else detect_adapter()
    resolved_root: Path = (
        repo_root if repo_root is not None else _discover_repo_root(resolved_adapter)
    )

    template_size_label = _template_size_label(round_type)
    expected_sections = _ROUND_TYPE_TO_TEMPLATE_SIZE[round_type]

    prior_summary = _read_prior_handoff(resolved_adapter, prior_round_anchor, resolved_root)

    brief = _build_planner_brief(
        round_name=round_name,
        round_type=round_type,
        prior_round_anchor=prior_round_anchor,
        scope_description=scope_description,
        template_size_label=template_size_label,
        prior_handoff_summary=prior_summary,
    )

    dispatch_result = resolved_adapter.dispatch_agent(
        agent_name="planner",
        prompt=brief,
        timeout_seconds=600,
    )

    if dispatch_result.exit_code != 0:
        return RunResult(
            handoff_path=None,
            section_count=0,
            loc=0,
            warnings=[],
            exit_code=1,
            error=(
                f"planner dispatch failed (exit {dispatch_result.exit_code}): "
                f"{dispatch_result.error}"
            ),
        )

    try:
        warnings, section_count, loc = _validate_planner_output(
            dispatch_result.output, expected_sections
        )
    except PlanRoundError as e:
        return RunResult(
            handoff_path=None,
            section_count=0,
            loc=0,
            warnings=[],
            exit_code=1,
            error=str(e),
        )

    handoff_path = _handoff_path(round_name, resolved_root)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_adapter.write_file(str(handoff_path), dispatch_result.output)

    return RunResult(
        handoff_path=handoff_path,
        section_count=section_count,
        loc=loc,
        warnings=warnings,
        exit_code=0,
        error=None,
    )
