from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from arcgentic.close_round import CloseRoundError, close_round


def _write_state(path: Path, *, state: str, commit: str | None = "a" * 40) -> None:
    payload = {
        "schema_version": "0.1",
        "project": {
            "name": "arcgentic",
            "root": str(path.parent),
            "round_naming": "v1",
            "paths": {"plans_dir": "docs/plans", "audits_dir": "docs/audits"},
            "session_mode": {"mode": "multi-session", "decided_at_round": "R1"},
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "auditor",
                "pending_thread_id": "auditor-1",
                "pending_since": "2026-06-03T00:00:00Z",
                "next_role": "planner",
            },
        },
        "current_round": {
            "id": "R-synthetic",
            "state": state,
            "state_history": [{"state": state, "ts": "2026-06-03T00:00:00Z", "by": "test"}],
            "audit_verdict": {
                "path": "verdict.md",
                "outcome": "PASS",
                "fact_table_total": 1,
                "fact_table_pass": 1,
            },
        },
        "states": {
            "passed": {"next": ["closed"]},
            "closed": {"next": []},
        },
        "last_passed_round": None,
        "mandates": [],
        "lessons": [],
        "active_debts": {"p0": 0, "p1": 0, "p2": 0, "p3": 0},
    }
    if commit is not None:
        payload["current_round"]["audit_verdict"]["commit"] = commit  # type: ignore[index]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_close_round_refuses_before_passed(tmp_path: Path) -> None:
    state = tmp_path / "state.yaml"
    verdict = tmp_path / "verdict.md"
    _write_state(state, state="awaiting_audit")
    verdict.write_text("# Verdict\n\n**Outcome:** PASS\n", encoding="utf-8")

    try:
        close_round(state_path=state, verdict_path=verdict, audit_commit="a" * 40)
    except CloseRoundError as exc:
        assert "state must be passed" in str(exc)
    else:
        raise AssertionError("expected CloseRoundError")


def test_close_round_refuses_unanchored_pass_verdict(tmp_path: Path) -> None:
    state = tmp_path / "state.yaml"
    verdict = tmp_path / "verdict.md"
    _write_state(state, state="passed", commit=None)
    verdict.write_text("# Verdict\n\n**Outcome:** PASS\n", encoding="utf-8")

    try:
        close_round(state_path=state, verdict_path=verdict, audit_commit="")
    except CloseRoundError as exc:
        assert "audit commit is required" in str(exc)
    else:
        raise AssertionError("expected CloseRoundError")


def test_close_round_closes_passed_round_and_records_last_passed(tmp_path: Path) -> None:
    state = tmp_path / "state.yaml"
    verdict = tmp_path / "verdict.md"
    _write_state(state, state="passed")
    verdict.write_text("# Verdict\n\n**Outcome:** PASS\n", encoding="utf-8")

    result = close_round(state_path=state, verdict_path=verdict, audit_commit="b" * 40)
    data = yaml.safe_load(state.read_text(encoding="utf-8"))

    assert result.closed is True
    assert result.lessons == 0
    assert result.amendments == 0
    assert data["current_round"]["state"] == "closed"
    assert data["last_passed_round"]["id"] == "R-synthetic"
    assert data["last_passed_round"]["commit"] == "b" * 40
    v2 = data["project"]["arcgentic_v2"]
    assert v2["orchestrator_status"] == "active"
    assert v2["round_status"] == "closed"
    assert "pending_role" not in v2
    assert "pending_thread_id" not in v2
    assert "pending_since" not in v2
    assert "next_role" not in v2


def test_close_round_refuses_verdict_when_strict_audit_check_fails(tmp_path: Path) -> None:
    state = tmp_path / "state.yaml"
    verdict = tmp_path / "verdict.md"
    _write_state(state, state="passed")
    verdict.write_text(
        "\n".join(
            [
                "# Verdict",
                "",
                "**Outcome:** PASS",
                "",
                "## § 7. Mechanical audit facts",
                "",
                "| # | Command | Expected | Comment |",
                "|---|---|---|---|",
                "| 1 | `bash -lc 'printf wrong'` | `right` | synthetic failing fact |",
                "",
                "## § 8. Verdict",
                "",
                "1 facts verified.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        close_round(state_path=state, verdict_path=verdict, audit_commit="c" * 40)
    except CloseRoundError as exc:
        assert "audit-check failed" in str(exc)
    else:
        raise AssertionError("expected CloseRoundError")
