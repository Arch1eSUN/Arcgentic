"""execute-round skill implementation.

Orchestrates the 4-commit chain per spec § 4.2.3:
- Phase 1 (commit 1 — entry-admin): handoff doc + CLAUDE.md state-row + vault sync
- Phase 2 (commit 2 — BA design pass): dispatch ba-designer → write BA design doc
- Phase 3 (commit 3 — dev body): dispatch developer → 4 quality gates → inline CR + SE
- Phase 4 (commit 4 — state refresh + audit handoff): compose + run audit-check

v0.2.0 P0 scope reductions (forward-debts in docs/tech-debt.md):
- ER-RETRY: no retry-with-context loops; fail-fast on first sub-agent error
- ER-AUDIT-GATE-4: gate 4 (audit-check) is SKIPPED — DONE_WITH_CONCERNS deviation
- ER-AUDIT-FACTS: audit facts table skeletoned with TODO markers
- ER-STATE-ROW: CLAUDE.md state-row update is a NO-OP

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 4.2
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from arcgentic.adapters import IDEAdapter, detect_adapter
from arcgentic.adapters._local_env import shquote

# ── Phase result structures ────────────────────────────────────────────

@dataclass(frozen=True)
class PhaseResult:
    """Result of one phase in the 4-commit chain."""

    phase_name: str  # "entry-admin" | "ba-design" | "dev-body" | "state-refresh"
    commit_sha: str | None  # None in dry_run mode
    files_touched: list[str] = field(default_factory=list)
    sub_agent_dispatched: str | None = None  # name of agent (e.g. "ba-designer")
    # gate_name → "PASS" / "FAIL" / "SKIPPED"
    quality_gates: dict[str, str] = field(default_factory=dict)
    deviations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecuteRoundResult:
    """End-to-end result of the 4-commit chain.

    exit_code semantics:
    - 0: all 4 phases succeeded (or all simulated in dry_run)
    - 1: a phase failed (e.g. agent dispatch error / quality gate FAIL)
    - 2: input error (handoff missing / round_name invalid)
    """

    round_name: str
    phases: list[PhaseResult]
    cr_findings_count: int = 0
    se_findings_count: int = 0
    quality_gate_summary: dict[str, str] = field(default_factory=dict)
    audit_handoff_path: Path | None = None
    audit_check_pass: bool = False  # SKIPPED for v0.2.0 P0
    exit_code: int = 0
    error: str | None = None
    dry_run: bool = False
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.error:
            return f"FAILED: {self.error}"
        lines = [
            f"execute-round {'(DRY RUN) ' if self.dry_run else ''}succeeded for {self.round_name}:"
        ]
        lines.append(f"  phases: {len(self.phases)} (entry-admin / BA / dev / state-refresh)")
        for p in self.phases:
            sha_disp = p.commit_sha[:12] if p.commit_sha else "<DRY-RUN>"
            lines.append(
                f"    - {p.phase_name}: commit={sha_disp}, files={len(p.files_touched)}"
            )
        lines.append(f"  CR findings: {self.cr_findings_count}")
        lines.append(f"  SE NOVEL findings: {self.se_findings_count}")
        lines.append(f"  audit handoff: {self.audit_handoff_path or '<DRY-RUN>'}")
        audit_status = (
            "PASS" if self.audit_check_pass
            else "SKIPPED (v0.2.0 P0 forward-debt ER-AUDIT-GATE-4)"
        )
        lines.append(f"  audit-check: {audit_status}")
        if self.warnings:
            lines.append(f"  warnings: {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)


# ── Errors ─────────────────────────────────────────────────────────────

class ExecuteRoundError(Exception):
    """Raised for fatal orchestration failures."""


# ── Constants ──────────────────────────────────────────────────────────

_QUALITY_GATES = ["mypy", "pytest", "ruff"]  # gate 4 (audit-check) is SKIPPED for v0.2.0 P0


# ── Helpers ────────────────────────────────────────────────────────────

def _read_handoff(adapter: IDEAdapter, handoff_path: Path) -> str:
    try:
        return adapter.read_file(str(handoff_path))
    except FileNotFoundError as e:
        raise ExecuteRoundError(f"Handoff not found at {handoff_path}: {e}") from e
    except OSError as e:
        raise ExecuteRoundError(f"Handoff not found at {handoff_path}: {e}") from e


def _extract_ba_brief_from_handoff(handoff_md: str) -> str:
    """Extract handoff § 4 'BA design pass brief' for dispatching ba-designer.

    Returns the § 4 body text. If not found, returns the full handoff (best-effort).
    """
    lines = handoff_md.splitlines()
    in_section = False
    section_body: list[str] = []
    for ln in lines:
        if ln.startswith("## 4."):
            in_section = True
            continue
        if in_section and ln.startswith("## ") and not ln.startswith("## 4."):
            break
        if in_section:
            section_body.append(ln)
    if not section_body:
        return handoff_md  # fallback: send whole handoff
    return "\n".join(section_body)


def _extract_se_threat_surfaces(handoff_md: str) -> list[str]:
    """Extract handoff § 14 'Security threat surfaces' subsections.

    Returns list of threat surface strings for SE CONTRACT-ONLY brief.
    """
    lines = handoff_md.splitlines()
    in_section = False
    threat_surfaces: list[str] = []
    for ln in lines:
        if ln.startswith("## 14."):
            in_section = True
            continue
        if in_section and ln.startswith("## ") and not ln.startswith("## 14."):
            break
        # Collect "### 14.N {threat}" entries
        if in_section and ln.startswith("### 14."):
            threat_surfaces.append(ln.replace("### 14.", "14.").strip())
    return threat_surfaces


def _round_to_upper(round_name: str) -> str:
    """Convert round_name to uppercase + underscore for BA_DESIGN filename.

    e.g. "R10-L3-aletheia" → "R10_L3_ALETHEIA"
    Dots are preserved: "R1.6.1" → "R1.6.1"
    """
    return round_name.replace("-", "_").upper()


def _ba_design_path(round_name: str, repo_root: Path) -> Path:
    return repo_root / "docs" / "design" / f"{_round_to_upper(round_name)}_BA_DESIGN.md"


def _audit_handoff_path(round_name: str, repo_root: Path) -> Path:
    """docs/audits/{round}.md — simplified path for v0.2.0 P0."""
    return repo_root / "docs" / "audits" / f"{round_name}.md"


def _discover_repo_root(adapter: IDEAdapter) -> Path:
    try:
        stdout, code = adapter.shell("git rev-parse --show-toplevel")
        if code == 0 and stdout.strip():
            return Path(stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def _run_quality_gates(
    adapter: IDEAdapter, repo_root: Path
) -> dict[str, str]:
    """Run mypy + pytest + ruff. Returns {gate_name: PASS/FAIL/SKIPPED}.

    Uses POSIX shell-quoting on repo_root path (the actual arcgentic repo path
    `/Users/archiesun/Desktop/Arc Studio/arcgentic` contains a space — unquoted
    interpolation would break every gate silently).

    Gate 4 (audit-check) is SKIPPED for v0.2.0 P0 — record as DONE_WITH_CONCERNS deviation.
    """
    results: dict[str, str] = {}
    rr = shquote(str(repo_root))
    rr_toolkit = shquote(str(repo_root / "toolkit"))
    # mypy
    _, code = adapter.shell(f"cd {rr} && mypy --strict toolkit/src/ toolkit/tests/")
    results["mypy"] = "PASS" if code == 0 else "FAIL"
    # pytest
    _, code = adapter.shell(f"cd {rr_toolkit} && pytest --tb=no -q")
    results["pytest"] = "PASS" if code == 0 else "FAIL"
    # ruff
    _, code = adapter.shell(f"cd {rr_toolkit} && ruff check .")
    results["ruff"] = "PASS" if code == 0 else "FAIL"
    # gate 4 audit-check SKIPPED for v0.2.0 P0 (forward-debt ER-AUDIT-GATE-4)
    results["audit-check"] = "SKIPPED (v0.2.0 P0 forward-debt ER-AUDIT-GATE-4)"
    return results


def _compose_self_audit_skeleton(
    round_name: str,
    phase_results: list[PhaseResult],
    cr_findings_md: str,
    se_findings_md: str,
    quality_gates: dict[str, str],
) -> str:
    """Compose self-audit handoff markdown (skeleton with TODO markers per ER-AUDIT-FACTS).

    Structure follows templates/self_audit_handoff.md (8 sections).
    """
    today = date.today().isoformat()
    sha_displays = {p.phase_name: (p.commit_sha or "<DRY-RUN>") for p in phase_results}

    ba_path_display = f"docs/design/{_round_to_upper(round_name)}_BA_DESIGN.md"

    # Pre-compose lines that would exceed 100 chars inside the f-string
    _m25 = (
        "- Mandate #25 (a): quality gates run pre-commit "
        "(mypy + pytest + ruff; gate 4 audit-check SKIPPED — see Deviations)"
    )
    _gate4_dev = (
        "- Gate 4 (audit-check) SKIPPED — `arcgentic audit-check` CLI not yet integrated "
        "(sub-phase d.1 forward-debt ER-AUDIT-GATE-4). "
        "Reporting DONE_WITH_CONCERNS per developer agent's contract."
    )
    _audit_facts_todo = (
        "TODO: auto-generate 25-40 mechanical audit facts via "
        "audit-check engine (ER-AUDIT-FACTS forward-debt)."
    )
    _state_sha = sha_displays.get("state-refresh", "HEAD")
    _fact_row = (
        f"| 1 | `git log --oneline {_state_sha} -n 4 \\| wc -l`"
        " | `4` | 4-commit chain present |"
    )
    _verdict_line = (
        "**STATUS: DONE_WITH_CONCERNS** — round complete; "
        "gate 4 (audit-check) SKIPPED per v0.2.0 P0 forward-debt ER-AUDIT-GATE-4."
    )

    return f"""# {round_name} — Self-Audit Handoff

**Round**: {round_name}
**Authoring agent**: execute-round skill (arcgentic v0.2.0-alpha.1)
**Date**: {today}
**Audit script**: `arcgentic audit-check docs/audits/{round_name}.md --strict-extended`

---

## § 1. Scope

### 1.1 Summary

Round {round_name} completed 4-commit chain orchestration via execute-round skill.

### 1.2 Mandate posture

- Mandate #17(d) clause (h) Option A: applied (inline BA + CR + SE finalization)
- Mandate #20 SE CONTRACT-ONLY: enforced (se-contract dispatched without BA design)
{_m25}

## § 2. Decisions Verified (BA + CR + SE three-way reconciliation)

### 2.1 BA design pass summary

BA design dispatched in Phase 2; output written to {ba_path_display}.

TODO: extract D-1..D-N decision summary from BA design doc (ER-AUDIT-FACTS forward-debt).

### 2.2 CR inline pass

{cr_findings_md or "(CR dispatch deferred / dry_run)"}

### 2.3 SE CONTRACT-ONLY pass (mandate #20)

{se_findings_md or "(SE dispatch deferred / dry_run)"}

## § 3. Toolkit + skill scan

| Skill / agent | Invocation count | Notes |
|---|---|---|
| execute-round | 1 | this round |
| ba-designer | 1 | Phase 2 dispatch |
| developer | 1 | Phase 3 dispatch |
| cr-reviewer | 1 | Phase 3 inline |
| se-contract | 1 | Phase 3 inline |

## § 4. Commits + CI evidence

```
Commit 1 (entry-admin):   {sha_displays.get('entry-admin', '<missing>')}
Commit 2 (BA design):     {sha_displays.get('ba-design', '<missing>')}
Commit 3 (dev body):      {sha_displays.get('dev-body', '<missing>')}
Commit 4 (state+audit):   {sha_displays.get('state-refresh', '<missing>')}  <- this commit
```

CI status: UNAVAILABLE — local 4-gate is canonical per mandate #25 (d)

## § 5. Quality gates

| Gate | Status |
|---|---|
| mypy --strict | {quality_gates.get('mypy', '?')} |
| pytest | {quality_gates.get('pytest', '?')} |
| ruff check . | {quality_gates.get('ruff', '?')} |
| arcgentic audit-check --strict-extended | {quality_gates.get('audit-check', '?')} |

### 5.1 Deviations

{_gate4_dev}

## § 6. Forward-debts (this round's delta)

### 6.1 Inherited from prior round

TODO: read prior audit handoff for inherited debts (ER-AUDIT-FACTS).

### 6.2 NEW from this round

(Round-specific forward-debts registered in docs/tech-debt.md during Phase 3.)

### 6.3 Aggregate count

TODO: count forward-debts before/after (ER-AUDIT-FACTS).

## § 7. Mechanical audit facts

{_audit_facts_todo}

| # | Command | Expected | Comment |
|---|---|---|---|
{_fact_row}

(Placeholder — real fact table generated by ER-AUDIT-FACTS once audit-check ships.)

## § 8. Verdict

{_verdict_line}

---

*Self-audit handoff for {round_name} written by execute-round skill (arcgentic v0.2.0-alpha.1).*
"""


# ── Phase functions (each is a Step in the 4-commit chain) ──────────────

def _phase_entry_admin(
    adapter: IDEAdapter,
    round_name: str,
    handoff_path: Path,
    repo_root: Path,
    dry_run: bool,
) -> PhaseResult:
    """Phase 1: entry-admin commit — handoff doc + state-row updates (no code).

    v0.2.0 P0: state-row update is NO-OP (ER-STATE-ROW forward-debt).
    If the handoff is already committed (the typical case after plan-round wrote it),
    Phase 1 is a no-op: returns PhaseResult with commit_sha=None + deviation note.
    """
    files_touched = [str(handoff_path)]
    if dry_run:
        return PhaseResult(
            phase_name="entry-admin",
            commit_sha=None,
            files_touched=files_touched,
        )

    # Check if handoff has any uncommitted changes
    stdout, _ = adapter.shell(
        f"cd {shquote(str(repo_root))} && git status --porcelain {shquote(str(handoff_path))}"
    )
    if not stdout.strip():
        # Handoff already committed — Phase 1 is a no-op
        return PhaseResult(
            phase_name="entry-admin",
            commit_sha=None,
            files_touched=files_touched,
            deviations=["handoff already committed; Phase 1 no-op"],
        )

    subject = f"docs({round_name}): entry-admin handoff"
    sha = adapter.git_commit(subject, files=files_touched)
    return PhaseResult(
        phase_name="entry-admin",
        commit_sha=sha,
        files_touched=files_touched,
    )


def _phase_ba_design(
    adapter: IDEAdapter,
    round_name: str,
    handoff_md: str,
    repo_root: Path,
    dry_run: bool,
) -> tuple[PhaseResult, str]:
    """Phase 2: BA design pass — dispatch ba-designer → write BA design doc.

    Returns (PhaseResult, ba_design_text). ba_design_text is needed by Phase 3 (developer).
    """
    ba_brief = _extract_ba_brief_from_handoff(handoff_md)
    result = adapter.dispatch_agent(
        agent_name="ba-designer",
        prompt=ba_brief,
        timeout_seconds=900,  # BA can be slow
    )
    if result.exit_code != 0:
        raise ExecuteRoundError(
            f"ba-designer dispatch failed (exit {result.exit_code}): {result.error}"
        )
    ba_design = result.output
    ba_path = _ba_design_path(round_name, repo_root)
    ba_path.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_file(str(ba_path), ba_design)

    if dry_run:
        return PhaseResult(
            phase_name="ba-design",
            commit_sha=None,
            files_touched=[str(ba_path)],
            sub_agent_dispatched="ba-designer",
        ), ba_design

    subject = f"docs({round_name}/design): BA design pass"
    sha = adapter.git_commit(subject, files=[str(ba_path)])
    return PhaseResult(
        phase_name="ba-design",
        commit_sha=sha,
        files_touched=[str(ba_path)],
        sub_agent_dispatched="ba-designer",
    ), ba_design


def _phase_dev_body(
    adapter: IDEAdapter,
    round_name: str,
    ba_design: str,
    handoff_md: str,
    repo_root: Path,
    dry_run: bool,
) -> tuple[PhaseResult, dict[str, str], int, int, str, str]:
    """Phase 3: dev body — dispatch developer + run quality gates + inline CR + SE.

    Returns (PhaseResult, quality_gates, cr_findings_count, se_findings_count,
             cr_findings_md, se_findings_md).

    Mandate #20: SE brief MUST NOT contain ba_design — pass only contract-extracted text.
    """
    ba_path = _ba_design_path(round_name, repo_root)

    # Dispatch developer
    dev_brief = (
        f"Implement the BA design for round {round_name} EXACTLY. The BA design doc was just "
        f"written to {ba_path}. Follow its file decomposition + "
        f"test plan + D-1..D-N decisions. Run 4 quality gates before reporting done."
        f"\n\nBA design follows:\n\n{ba_design}"
    )
    dev_result = adapter.dispatch_agent(
        agent_name="developer",
        prompt=dev_brief,
        timeout_seconds=1800,  # dev can be long
    )
    if dev_result.exit_code != 0:
        raise ExecuteRoundError(
            f"developer dispatch failed (exit {dev_result.exit_code}): {dev_result.error}"
        )

    # Run quality gates locally
    quality_gates = _run_quality_gates(adapter, repo_root)
    gate_failures = [g for g, s in quality_gates.items() if s == "FAIL"]
    if gate_failures:
        # v0.2.0 P0: fail-fast (no retry; ER-RETRY forward-debt)
        raise ExecuteRoundError(
            f"Phase 3 quality gates failed: {gate_failures}. Re-invoke after fixing."
        )

    # Inline CR step — sees BA design (per spec § 5.4)
    cr_brief = (
        f"Review the dev-body diff for round {round_name}. BA design was at "
        f"{ba_path}; dev output follows. Produce a "
        f"P0/P1/P2/P3 findings table.\n\nDev output:\n\n{dev_result.output}\n\n"
        f"BA design:\n\n{ba_design}"
    )
    cr_result = adapter.dispatch_agent(
        agent_name="cr-reviewer",
        prompt=cr_brief,
        timeout_seconds=600,
    )
    if cr_result.exit_code != 0:
        raise ExecuteRoundError(f"cr-reviewer dispatch failed: {cr_result.error}")
    cr_findings_md = cr_result.output
    cr_findings_count = cr_findings_md.count("| CR-")

    # Inline SE step — CONTRACT-ONLY per mandate #20 (NO BA design in brief)
    threat_surfaces = _extract_se_threat_surfaces(handoff_md)
    # Use dev_result.output as the contract surface
    contract_text = dev_result.output
    se_brief = (
        f"Perform CONTRACT-ONLY security review for round {round_name}. Per MANDATE #20, "
        f"you receive ONLY the contract text + threat surfaces — NOT the BA design.\n\n"
        f"Threat surfaces:\n"
        + "\n".join(f"- {ts}" for ts in threat_surfaces)
        + f"\n\nContract text:\n\n{contract_text}"
    )

    # MANDATE #20 enforcement: assert BA design is NOT in se_brief
    # Check for BA design content markers that should NOT appear in the SE brief's
    # contract_text (which comes from dev_result.output).
    # Use round-specific word-boundary regex to avoid false positives on benign
    # substrings like `config_BA_DESIGN_constant` — only the exact round-prefixed
    # marker `{ROUND_UPPER}_BA_DESIGN` (word-bounded) triggers the violation.
    round_upper = _round_to_upper(round_name)
    ba_design_marker_re = re.compile(rf"\b{re.escape(round_upper)}_BA_DESIGN\b")
    if ba_design_marker_re.search(contract_text) or ba_design_marker_re.search(se_brief):
        raise ExecuteRoundError(
            f"MANDATE #20 violation: round-specific BA design marker "
            f"`{round_upper}_BA_DESIGN` detected in dev output / SE brief. "
            f"Refusing to dispatch se-contract (CONTRACT-ONLY isolation must hold)."
        )

    se_result = adapter.dispatch_agent(
        agent_name="se-contract",
        prompt=se_brief,
        timeout_seconds=600,
    )
    if se_result.exit_code != 0:
        raise ExecuteRoundError(f"se-contract dispatch failed: {se_result.error}")
    se_findings_md = se_result.output
    se_findings_count = se_findings_md.count("| SE-")

    if dry_run:
        return PhaseResult(
            phase_name="dev-body",
            commit_sha=None,
            files_touched=["<dev-body files; dry_run>"],
            sub_agent_dispatched="developer",
            quality_gates=quality_gates,
        ), quality_gates, cr_findings_count, se_findings_count, cr_findings_md, se_findings_md

    stdout, _ = adapter.shell(
        f"cd {shquote(str(repo_root))} && git diff --staged --name-only"
    )
    files_touched = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not files_touched:
        raise ExecuteRoundError(
            "Phase 3: developer dispatch produced no staged files. The developer agent "
            "should stage its output before reporting done."
        )
    subject = f"feat({round_name}): {round_name} dev body"
    sha = adapter.git_commit(subject)
    return PhaseResult(
        phase_name="dev-body",
        commit_sha=sha,
        files_touched=files_touched,
        sub_agent_dispatched="developer",
        quality_gates=quality_gates,
    ), quality_gates, cr_findings_count, se_findings_count, cr_findings_md, se_findings_md


def _phase_state_refresh(
    adapter: IDEAdapter,
    round_name: str,
    phase_results: list[PhaseResult],
    cr_findings_md: str,
    se_findings_md: str,
    quality_gates: dict[str, str],
    repo_root: Path,
    dry_run: bool,
) -> PhaseResult:
    """Phase 4: state refresh + self-audit handoff."""
    self_audit_md = _compose_self_audit_skeleton(
        round_name=round_name,
        phase_results=phase_results,
        cr_findings_md=cr_findings_md,
        se_findings_md=se_findings_md,
        quality_gates=quality_gates,
    )
    audit_path = _audit_handoff_path(round_name, repo_root)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_file(str(audit_path), self_audit_md)

    if dry_run:
        return PhaseResult(
            phase_name="state-refresh",
            commit_sha=None,
            files_touched=[str(audit_path)],
            deviations=["gate 4 audit-check SKIPPED (v0.2.0 P0 ER-AUDIT-GATE-4)"],
        )

    subject = f"docs(audit/{round_name}): {round_name} self-audit handoff + state refresh"
    sha = adapter.git_commit(subject, files=[str(audit_path)])
    return PhaseResult(
        phase_name="state-refresh",
        commit_sha=sha,
        files_touched=[str(audit_path)],
        deviations=["gate 4 audit-check SKIPPED (v0.2.0 P0 ER-AUDIT-GATE-4)"],
    )


# ── Public entry point ─────────────────────────────────────────────────

def run(
    *,
    round_name: str,
    handoff_path: Path,
    dry_run: bool = False,
    adapter: IDEAdapter | None = None,
    repo_root: Path | None = None,
) -> ExecuteRoundResult:
    """Execute the 4-commit chain for a planned round.

    Args:
        round_name: e.g. "R10-L3-aletheia"
        handoff_path: path to the planned handoff doc (from plan-round)
        dry_run: if True, skip all git commits but **still write generated files to disk**
            (BA design doc at docs/design/{ROUND_UPPER}_BA_DESIGN.md and self-audit handoff
            at docs/audits/{round_name}.md). Use dry_run to preview the orchestration's
            artifact production without polluting git history; the on-disk files allow
            inspection of what would have been committed.
        adapter: defaults to detect_adapter()
        repo_root: defaults to git rev-parse --show-toplevel

    Exit code semantics:
    - 0: all 4 phases succeeded (or simulated in dry_run)
    - 1: a phase failed
    - 2: input error (handoff missing / invalid)
    """
    if adapter is None:
        adapter = detect_adapter()
    if repo_root is None:
        repo_root = _discover_repo_root(adapter)

    try:
        handoff_md = _read_handoff(adapter, handoff_path)
    except ExecuteRoundError as e:
        return ExecuteRoundResult(
            round_name=round_name,
            phases=[],
            exit_code=2,
            error=str(e),
            dry_run=dry_run,
        )

    phases: list[PhaseResult] = []
    warnings: list[str] = [
        "gate 4 audit-check SKIPPED (v0.2.0 P0 ER-AUDIT-GATE-4)"
    ]

    try:
        # Phase 1
        p1 = _phase_entry_admin(adapter, round_name, handoff_path, repo_root, dry_run)
        phases.append(p1)

        # Phase 2
        p2, ba_design = _phase_ba_design(adapter, round_name, handoff_md, repo_root, dry_run)
        phases.append(p2)

        # Phase 3
        p3, quality_gates, cr_count, se_count, cr_md, se_md = _phase_dev_body(
            adapter, round_name, ba_design, handoff_md, repo_root, dry_run
        )
        phases.append(p3)

        # Phase 4
        p4 = _phase_state_refresh(
            adapter, round_name, phases, cr_md, se_md, quality_gates, repo_root, dry_run
        )
        phases.append(p4)

    except ExecuteRoundError as e:
        return ExecuteRoundResult(
            round_name=round_name,
            phases=phases,
            exit_code=1,
            error=str(e),
            dry_run=dry_run,
            warnings=warnings,
        )

    audit_path = _audit_handoff_path(round_name, repo_root)
    return ExecuteRoundResult(
        round_name=round_name,
        phases=phases,
        cr_findings_count=cr_count,
        se_findings_count=se_count,
        quality_gate_summary=quality_gates,
        audit_handoff_path=audit_path,
        audit_check_pass=False,  # SKIPPED per v0.2.0 P0
        exit_code=0,
        error=None,
        dry_run=dry_run,
        warnings=warnings,
    )
