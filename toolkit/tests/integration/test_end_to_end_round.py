"""End-to-end integration test for arcgentic v0.2.0 P0.

Exercises the full plan_round → execute_round pipeline. Both skills are invoked
with a multi-stub adapter that returns canned outputs per agent_name. Real
filesystem (tmp_path) but no real git, no real subprocess, no real LLM.

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 21.5
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arcgentic.adapters.base import AgentDispatchResult
from arcgentic.adapters.inline import InlineAdapter
from arcgentic.skills_impl.execute_round import run as execute_round_run
from arcgentic.skills_impl.plan_round import run as plan_round_run

# Marker so tests can be deselected with `-m "not integration"`
pytestmark = pytest.mark.integration


class _E2EStubAdapter(InlineAdapter):
    """Multi-agent stub for end-to-end integration:
    - planner: returns a valid 18-section handoff doc
    - ba-designer: returns a valid BA design doc
    - developer: returns a valid dev summary
    - cr-reviewer: returns a valid CR findings table
    - se-contract: returns a valid SE findings table

    Also overrides shell() to mock quality gates as PASS.
    """

    def __init__(self) -> None:
        self._canned: dict[str, str] = {
            "planner": self._fake_handoff_18(),
            "ba-designer": self._fake_ba_design(),
            "developer": "Implemented per BA. Files: src/foo.py, src/bar.py. Tests PASS.",
            "cr-reviewer": (
                "| ID | Sev | Finding | Disposition |\n"
                "|---|---|---|---|\n"
                "| CR-1 | P3 | Minor naming inconsistency in foo.py | Inline-closed |\n"
                "| CR-2 | P3 | Missing docstring in bar.py | Inline-closed |\n"
                "| CR-3 | P3 | Consider extracting helper | Forward-debt: HELPER-EXTRACT |\n"
            ),
            "se-contract": (
                "| ID | Sev | Threat surface | Finding | Disposition |\n"
                "|---|---|---|---|---|\n"
                "| SE-1 | P3 | prompt-injection | Input bounds check | Forward-debt: BOUNDS |\n"
                "| SE-2 | P3 | cost-discipline | No paid-API imports — verified | Inline-closed |\n"
                "| SE-3 | P3 | replay-determinism | Pure function verified | Inline-closed |\n"
            ),
        }

    def dispatch_agent(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 600,
        isolation: str | None = None,
    ) -> AgentDispatchResult:
        return AgentDispatchResult(
            output=self._canned.get(agent_name, ""),
            exit_code=0,
            duration_ms=10,
            agent_type=agent_name,
            error=None,
        )

    def shell(self, command: str, timeout_seconds: int = 120) -> tuple[str, int]:
        # Mock all quality gate + git commands as success
        if "git rev-parse --show-toplevel" in command:
            return "/tmp/test-repo", 0
        if "git status --porcelain" in command:
            return "?? new-file.md", 0  # something to commit (Phase 1 non-dry)
        if "git diff --staged" in command:
            return "src/foo.py\nsrc/bar.py", 0
        if "mypy" in command or "pytest" in command or "ruff" in command:
            return "ok", 0
        # Fallback to inline adapter's real shell (won't be reached in these tests)
        return super().shell(command, timeout_seconds)

    @staticmethod
    def _fake_handoff_18() -> str:
        """Return a valid 18-section handoff doc."""
        sections = "\n\n".join(
            f"## {i}. Section {i} Title\n\nBody content for section {i}.\n"
            for i in range(1, 19)
        )
        return f"""# R10-L3-test — Entry-Admin + Dev Handoff

**Phase**: Phase 10 test
**Round**: R10-L3-test (R1)
**Type**: substrate-touching round
**Mandate level**: Mandate #17(d) FULL-STRENGTH; clause (h) Option A 1st round
**Prior-round anchor**: `{"a" * 40}` (genesis)
**Audit script**: `arcgentic audit-check docs/audits/phase-10/R10-L3-test.md --strict-extended`
**CI status**: UNAVAILABLE — local-substitute MANDATORY

---

{sections}

---

*Entry-admin handoff written by planner agent (arcgentic v0.2.0-alpha.1).*
"""

    @staticmethod
    def _fake_ba_design() -> str:
        """Return a minimal valid BA design doc.

        NO `_BA_DESIGN` marker in the body to avoid MANDATE #20 false positives.
        The title heading `# {ROUND}_BA_DESIGN` is the BA doc itself; MANDATE #20
        only guards against the marker appearing in DEV OUTPUT (not the BA doc).
        """
        return """# R10_L3_TEST_BA_DESIGN

**Round**: R10-L3-test
**Authoring agent**: ba-designer

---

## § 0. Round Context

Test round for end-to-end integration.

## § 1. Reference Scan

| # | Reference | Why used | What part | License + RT |
|---|---|---|---|---|
| 1 | stdlib pathlib | path manipulation | Path class | PSF + RT3 |

## § 3. Substrate Architecture

### 3.1 Decision D-1: Use Pydantic v2 frozen models

**Decision**: All data classes use `@dataclass(frozen=True)`.

**Rationale**:
1. Immutability prevents accidental mutation across the 4-commit chain.
2. Hashability enables use in sets and dict keys.
3. Frozen is the spec § 1 default.

**Alternatives rejected**:
- Mutable dataclasses — rejected: spec § 1 mandates frozen.

## § N. File-Level Decomposition

| File | Type | Est. LOC | Purpose |
|---|---|---|---|
| src/foo.py | source | 50 | foo logic |
| src/bar.py | source | 30 | bar helpers |

## § N+1. Test Plan

| Test file | Tests | Coverage focus |
|---|---|---|
| test_foo.py | test_basic, test_edge | foo happy path + edges |

## § N+2. Anti-scope Explicit

- NOT delivered: networking layer — deferred to next round.

---

*BA design for R10-L3-test written by ba-designer agent (arcgentic v0.2.0-alpha.1).*
"""


def test_end_to_end_plan_then_execute(tmp_path: Path) -> None:
    """plan-round → execute-round end-to-end with dry_run=True.

    Verifies:
    - plan_round.run produces handoff at docs/superpowers/plans/...
    - execute_round.run consumes that handoff
    - 4 phases all succeed
    - CR/SE findings counts > 0
    - audit handoff written (under tmp_path)
    """
    adapter = _E2EStubAdapter()

    # Phase 1: plan-round
    plan_result = plan_round_run(
        round_name="R10-L3-test",
        round_type="substrate-touching",
        prior_round_anchor="a" * 40,
        scope_description="End-to-end integration test",
        adapter=adapter,
        repo_root=tmp_path,
    )
    assert plan_result.exit_code == 0, f"plan_round failed: {plan_result.error}"
    assert plan_result.handoff_path is not None
    assert plan_result.handoff_path.exists()
    assert plan_result.section_count == 18

    # Phase 2: execute-round (dry_run so no git commits)
    er_result = execute_round_run(
        round_name="R10-L3-test",
        handoff_path=plan_result.handoff_path,
        dry_run=True,
        adapter=adapter,
        repo_root=tmp_path,
    )
    assert er_result.exit_code == 0, f"execute_round failed: {er_result.error}"
    assert len(er_result.phases) == 4
    # All commit_sha=None because dry_run
    assert all(p.commit_sha is None for p in er_result.phases)
    # CR + SE findings > 0
    assert er_result.cr_findings_count == 3
    assert er_result.se_findings_count == 3
    # Audit handoff written to disk
    assert er_result.audit_handoff_path is not None
    assert er_result.audit_handoff_path.exists()
    # Audit handoff contains expected structure
    audit_md = er_result.audit_handoff_path.read_text(encoding="utf-8")
    assert "## § 1. Scope" in audit_md
    assert "## § 8. Verdict" in audit_md
    assert "STATUS: DONE_WITH_CONCERNS" in audit_md  # gate 4 SKIPPED per v0.2.0 P0


def test_end_to_end_audit_handoff_structure(tmp_path: Path) -> None:
    """End-to-end produces audit handoff matching templates/self_audit_handoff.md spec § 9."""
    adapter = _E2EStubAdapter()
    plan_result = plan_round_run(
        round_name="R10-L3-structtest",
        round_type="substrate-touching",
        prior_round_anchor="b" * 40,
        scope_description="Structural test",
        adapter=adapter,
        repo_root=tmp_path,
    )
    assert plan_result.exit_code == 0
    er_result = execute_round_run(
        round_name="R10-L3-structtest",
        handoff_path=plan_result.handoff_path,  # type: ignore[arg-type]
        dry_run=True,
        adapter=adapter,
        repo_root=tmp_path,
    )
    assert er_result.exit_code == 0
    assert er_result.audit_handoff_path is not None
    audit_md = er_result.audit_handoff_path.read_text(encoding="utf-8")
    # Spec § 9 requires sections § 1-§ 8
    for section_num in range(1, 9):
        assert f"## § {section_num}." in audit_md, f"missing § {section_num}"
    # MANDATE #20 mention in self-audit § 2.3
    assert "SE CONTRACT-ONLY" in audit_md
    assert "mandate #20" in audit_md.lower()


def test_end_to_end_handoff_compositional(tmp_path: Path) -> None:
    """The handoff produced by plan-round must be CONSUMABLE by execute-round.

    This is the integration value: not just that each works alone, but that
    they share a contract.
    """
    adapter = _E2EStubAdapter()
    plan_round_run(
        round_name="R10-L3-compose",
        round_type="substrate-touching",
        prior_round_anchor="c" * 40,
        scope_description="Composition test",
        adapter=adapter,
        repo_root=tmp_path,
    )
    # plan-round wrote a handoff at expected path
    expected_handoff_pattern = tmp_path / "docs/superpowers/plans"
    assert expected_handoff_pattern.is_dir()
    handoffs = list(expected_handoff_pattern.glob("*-R10-L3-compose-handoff.md"))
    assert len(handoffs) == 1
    handoff = handoffs[0]
    # The handoff has the expected 18-section structure
    assert handoff.read_text(encoding="utf-8").count("\n## ") == 18

    # execute-round can read + orchestrate from this handoff
    er_result = execute_round_run(
        round_name="R10-L3-compose",
        handoff_path=handoff,
        dry_run=True,
        adapter=adapter,
        repo_root=tmp_path,
    )
    assert er_result.exit_code == 0
    # BA design path uses _round_to_upper convention
    expected_ba_path = tmp_path / "docs/design/R10_L3_COMPOSE_BA_DESIGN.md"
    assert expected_ba_path.exists()


def test_end_to_end_invalid_handoff_fails_execute_round(tmp_path: Path) -> None:
    """If plan-round produces a handoff with wrong section count, execute-round is never reached.

    plan_round should reject the broken planner output with exit_code=1 (wrong section count);
    execute_round is never invoked.
    """

    # Adapter where planner returns INVALID 5-section handoff
    class _BrokenPlannerStub(_E2EStubAdapter):
        def dispatch_agent(
            self,
            agent_name: str,
            prompt: str,
            timeout_seconds: int = 600,
            isolation: str | None = None,
        ) -> AgentDispatchResult:
            if agent_name == "planner":
                broken = "# R10-L3-broken\n\n" + "\n".join(
                    f"## {i}. Sec\n\nbody" for i in range(1, 6)  # only 5 sections, not 18
                )
                return AgentDispatchResult(
                    output=broken,
                    exit_code=0,
                    duration_ms=10,
                    agent_type=agent_name,
                    error=None,
                )
            return super().dispatch_agent(agent_name, prompt, timeout_seconds, isolation)

    adapter = _BrokenPlannerStub()
    plan_result = plan_round_run(
        round_name="R10-L3-broken",
        round_type="substrate-touching",
        prior_round_anchor="d" * 40,
        adapter=adapter,
        repo_root=tmp_path,
    )
    assert plan_result.exit_code == 1
    assert "5 sections" in (plan_result.error or "")
    assert plan_result.handoff_path is None
