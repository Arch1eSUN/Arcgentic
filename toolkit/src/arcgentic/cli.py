"""arcgentic CLI entry point — `arcgentic <subcommand> [args]`.

Subcommands wired in this module:
- `arcgentic plan-round-impl --round=R --type=T --anchor=SHA [--scope=...]`
  → calls skills_impl.plan_round.run(...)
- `arcgentic execute-round-impl --round=R --handoff=PATH [--dry-run]`
  → calls skills_impl.execute_round.run(...)
- `arcgentic audit-check <audit_file> [--strict|--strict-extended]`
  → calls audit_check.main(...)
- `arcgentic validate-handoff <handoff_file>`
  → validates Moirai-derived source-rule handoff contract
- `arcgentic codify-lesson`
  → scans audits for recurring P2/P3 patterns and writes lesson cards
- `arcgentic track-refs ...`
  → classifies local reference repos and maintains references/INDEX.md
- `arcgentic round-boundary-lesson-scan`
  → hook wrapper around codify-lesson threshold detection
- `arcgentic cross-session-handoff <action>`
  → manages .arcgentic/state.yaml with TTL locks and atomic writes
- `arcgentic v2-session-plan --state <state.yaml> --host codex`
  → emits fixed-role Codex session orchestration JSON
- `arcgentic v2-record-session --state <state.yaml> --role developer --thread-id <id>`
  → records a fixed-role host session in state.yaml
- `arcgentic v2-dispatch-role --state <state.yaml> --role developer --thread-id <id>`
  → marks the Orchestrator sleeping after dispatching one role turn
- `arcgentic v2-return-signal --state <state.yaml> --signal-json <json>`
  or `--signal-text <natural-language-return-with-footer>`
  → wakes the Orchestrator, records a role return signal, and prints next routing JSON
- `arcgentic claude-code-broker install-hooks|handle-stop`
  → installs and runs the Claude Code hook-backed V2 broker transport
- `arcgentic mcp-serve`
  → runs the MCP server (stdio) exposing the round-status panel via MCP Apps

CLI is the bridge between markdown skills (which shell out via Claude Code's
Bash tool) and the Python toolkit (which holds the actual algorithms).
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="arcgentic",
        description="arcgentic Python CLI — algorithm backend for the Claude Code plugin.",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    # plan-round-impl
    plan_round_parser = subparsers.add_parser(
        "plan-round-impl",
        help="Generate a complete round handoff doc.",
    )
    plan_round_parser.add_argument(
        "--round",
        dest="round_name",
        required=True,
        help='Round name (e.g. "R10-L3-aletheia" or "R1.6.1")',
    )
    plan_round_parser.add_argument(
        "--type",
        dest="round_type",
        required=True,
        choices=[
            "substrate-touching",
            "fix-round",
            "entry-admin",
            "close-admin",
            "meta-admin-sweep",
        ],
        help="Round type — selects template size",
    )
    plan_round_parser.add_argument(
        "--anchor",
        dest="prior_round_anchor",
        required=True,
        help="Full 40-char SHA of prior round's last commit",
    )
    plan_round_parser.add_argument(
        "--scope",
        dest="scope_description",
        default="",
        help="1-3 sentence scope statement (optional; can be filled in handoff)",
    )

    # execute-round-impl
    execute_round_parser = subparsers.add_parser(
        "execute-round-impl",
        help="Execute the 4-commit chain for a planned round.",
    )
    execute_round_parser.add_argument(
        "--round",
        dest="round_name",
        required=True,
        help='Round name (e.g. "R10-L3-aletheia")',
    )
    execute_round_parser.add_argument(
        "--handoff",
        dest="handoff_path",
        required=True,
        help="Path to the planned handoff doc (from plan-round)",
    )
    execute_round_parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Skip all git commits; return planned phases",
    )

    # audit-check
    audit_check_parser = subparsers.add_parser(
        "audit-check",
        help="Verify mechanical facts in an audit handoff doc.",
    )
    audit_check_parser.add_argument(
        "audit_file",
        help="Path to audit handoff markdown",
    )
    audit_check_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any FAIL or SKIP",
    )
    audit_check_parser.add_argument(
        "--strict-extended",
        action="store_true",
        dest="strict_extended",
        help="Also run AC-1 (3 clauses) + AC-3 checks; exit 1 on violation",
    )

    # quality-gate-enforce
    quality_gate_parser = subparsers.add_parser(
        "quality-gate-enforce",
        help="Run all 4 quality gates (mypy + pytest + ruff + audit-check).",
    )
    quality_gate_parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        help="Repo root path (defaults to git rev-parse --show-toplevel)",
    )
    quality_gate_parser.add_argument(
        "--audit-handoff",
        dest="audit_handoff",
        default=None,
        help="Path to audit handoff for gate 4",
    )
    quality_gate_parser.add_argument(
        "--skip-audit-check",
        action="store_true",
        help="Skip gate 4 (audit-check)",
    )

    # validate-handoff
    validate_handoff_parser = subparsers.add_parser(
        "validate-handoff",
        help="Validate a planning handoff against the source-rule contract.",
    )
    validate_handoff_parser.add_argument(
        "handoff_file",
        help="Path to planning handoff markdown",
    )

    # codify-lesson
    codify_parser = subparsers.add_parser(
        "codify-lesson",
        help="Detect recurring audit patterns and promote lessons.",
    )
    codify_parser.add_argument("--audit-dir", default="docs/audits")
    codify_parser.add_argument("--lessons-dir", default="lessons")
    codify_parser.add_argument("--amendments-dir", default="mandates/amendments")
    codify_parser.add_argument("--N", type=int, default=10)
    codify_parser.add_argument("--dry-run", action="store_true")

    # track-refs
    track_refs_parser = subparsers.add_parser(
        "track-refs",
        help="Maintain references/INDEX.md and emit BA triplet rows.",
    )
    track_refs_sub = track_refs_parser.add_subparsers(dest="track_refs_command", required=True)
    track_add = track_refs_sub.add_parser("add")
    track_add.add_argument("repo_path")
    track_add.add_argument("--owner-repo", required=True)
    track_add.add_argument("--round", dest="round_name", required=True)
    track_add.add_argument("--index", default="references/INDEX.md")
    track_add.add_argument("--usage-evidence", required=True)
    track_add.add_argument("--relevance", default="medium")
    track_triplet = track_refs_sub.add_parser("triplet")
    track_triplet.add_argument("repo_path")
    track_triplet.add_argument("--owner-repo", required=True)
    track_triplet.add_argument("--round", dest="round_name", required=True)
    track_triplet.add_argument("--usage-evidence", required=True)
    track_refresh = track_refs_sub.add_parser("refresh-relevance")
    track_refresh.add_argument("--index", default="references/INDEX.md")
    track_refresh.add_argument("--round", dest="round_name", required=True)
    track_refresh.add_argument("--default-relevance", default="none")

    # round-boundary-lesson-scan
    lesson_scan_parser = subparsers.add_parser(
        "round-boundary-lesson-scan",
        help="Scan recent audits and invoke codify-lesson when thresholds are met.",
    )
    lesson_scan_parser.add_argument("--N", type=int, default=10)
    lesson_scan_parser.add_argument("--audit-dir", default="docs/audits")
    lesson_scan_parser.add_argument("--lessons-dir", default="lessons")
    lesson_scan_parser.add_argument("--amendments-dir", default="mandates/amendments")
    lesson_scan_parser.add_argument("--dry-run", action="store_true")

    # cross-session-handoff
    cross_parser = subparsers.add_parser(
        "cross-session-handoff",
        help="Manage shared .arcgentic/state.yaml across sessions.",
    )
    cross_sub = cross_parser.add_subparsers(dest="cross_command", required=True)
    cross_read = cross_sub.add_parser("read")
    cross_read.add_argument("--state", default=".arcgentic/state.yaml")
    cross_write = cross_sub.add_parser("write")
    cross_write.add_argument("--state", default=".arcgentic/state.yaml")
    cross_write.add_argument("--session-id", required=True)
    cross_write.add_argument("--updates", required=True)
    cross_write.add_argument("--ttl", type=int, default=600)
    cross_snapshot = cross_sub.add_parser("snapshot")
    cross_snapshot.add_argument("--state", default=".arcgentic/state.yaml")
    cross_snapshot.add_argument("--session-id", required=True)
    cross_snapshot.add_argument("--history-dir", default=None)
    cross_snapshot.add_argument("--ttl", type=int, default=1800)
    cross_acquire = cross_sub.add_parser("acquire-lock")
    cross_acquire.add_argument("--state", default=".arcgentic/state.yaml")
    cross_acquire.add_argument("--session-id", required=True)
    cross_acquire.add_argument("--ttl", type=int, default=1800)
    cross_release = cross_sub.add_parser("release-lock")
    cross_release.add_argument("--state", default=".arcgentic/state.yaml")
    cross_release.add_argument("--session-id", required=True)

    # V1: session-mode
    session_parser = subparsers.add_parser(
        "session-mode",
        help="Recommend or prompt single-session vs multi-session execution mode.",
    )
    session_sub = session_parser.add_subparsers(dest="session_command", required=True)
    session_recommend = session_sub.add_parser("recommend")
    session_recommend.add_argument("--round", dest="round_name", required=True)
    session_recommend.add_argument("--handoff", required=True)
    session_recommend.add_argument("--dispatch-unavailable", action="store_true")
    session_recommend_v2 = session_sub.add_parser("recommend-v2")
    session_recommend_v2.add_argument("--idea", required=True)
    session_prompt = session_sub.add_parser("prompt")
    session_prompt.add_argument("--round", dest="round_name", required=True)
    session_prompt.add_argument("--handoff", required=True)
    session_prompt.add_argument(
        "--mode",
        choices=["single-session", "multi-session"],
        required=True,
    )
    session_prompt.add_argument(
        "--role",
        choices=["developer", "auditor", "closeout"],
        default="developer",
    )

    dispatch_parser = subparsers.add_parser(
        "orchestrator-dispatch",
        help="Emit role dispatch order for a round handoff.",
    )
    dispatch_parser.add_argument("--round", dest="round_name", required=True)
    dispatch_parser.add_argument("--handoff", required=True)
    dispatch_parser.add_argument(
        "--mode",
        choices=["single-session", "multi-session"],
        required=True,
    )

    # V1: source-intake
    source_parser = subparsers.add_parser(
        "source-intake",
        help="Validate auditable source-intake YAML records.",
    )
    source_sub = source_parser.add_subparsers(dest="source_command", required=True)
    source_validate = source_sub.add_parser("validate")
    source_validate.add_argument("records", nargs="+")

    # V1: capability-registry
    capability_parser = subparsers.add_parser(
        "capability-registry",
        help="Build a normalized capability registry from marketplace catalogs.",
    )
    capability_sub = capability_parser.add_subparsers(dest="capability_command", required=True)
    capability_build = capability_sub.add_parser("build")
    capability_build.add_argument("catalogs", nargs="+")
    capability_build.add_argument("--output", default=None)

    # V1: spec-governance
    spec_parser = subparsers.add_parser(
        "spec-governance",
        help="Validate OpenSpec-style artifact graphs.",
    )
    spec_sub = spec_parser.add_subparsers(dest="spec_command", required=True)
    for command_name in ("status", "validate", "archive"):
        spec_cmd = spec_sub.add_parser(command_name)
        spec_cmd.add_argument("change_dir")
        spec_cmd.add_argument("--archive-root", default=None)

    # V1: agency-roster
    agency_parser = subparsers.add_parser(
        "agency-roster",
        help="Inspect agency-agents-style role catalogs.",
    )
    agency_sub = agency_parser.add_subparsers(dest="agency_command", required=True)
    agency_inspect = agency_sub.add_parser("inspect")
    agency_inspect.add_argument("catalog_path")

    # V1: release-readiness
    release_parser = subparsers.add_parser(
        "v1-release-readiness",
        help="Verify V1 release version and local install surfaces.",
    )
    release_parser.add_argument("--repo-root", default=".")
    release_parser.add_argument("--expected-version", default=None)
    release_parser.add_argument("--local-install-path", default=None)

    verdict_parser = subparsers.add_parser(
        "verdict-completeness",
        help="Validate PASS/NEEDS_FIX/AUDIT_INCOMPLETE verdict structure.",
    )
    verdict_parser.add_argument("verdict_file")

    close_parser = subparsers.add_parser(
        "close-round",
        help="Close a passed round after external audit PASS.",
    )
    close_parser.add_argument("--state-file", required=True)
    close_parser.add_argument("--verdict", required=True)
    close_parser.add_argument("--audit-commit", required=True)

    v2_session_parser = subparsers.add_parser(
        "v2-session-plan",
        help="Emit a V2 fixed-role session plan for a host platform.",
    )
    v2_session_parser.add_argument("--state", required=True)
    v2_session_parser.add_argument("--host", choices=["codex", "claude-code-broker"], required=True)
    v2_session_parser.add_argument("--user-request", default="")
    v2_session_parser.add_argument(
        "--mode",
        choices=["single-session-subagent", "multi-session-subthread"],
        default=None,
        help="Persist the project-level V2 mode after the user chooses it.",
    )

    v2_record_parser = subparsers.add_parser(
        "v2-record-session",
        help="Record a V2 fixed-role host session in state.yaml.",
    )
    v2_record_parser.add_argument("--state", required=True)
    v2_record_parser.add_argument(
        "--role",
        choices=["orchestrator", "planner", "developer", "test", "auditor"],
        required=True,
    )
    v2_record_parser.add_argument("--thread-id", required=True)
    v2_record_parser.add_argument("--title", default=None)
    v2_record_parser.add_argument(
        "--repair-current-orchestrator",
        action="store_true",
        help="Repair only the current Orchestrator push-return target.",
    )
    v2_record_parser.add_argument(
        "--host",
        choices=["codex", "claude-code-broker"],
        default="codex",
    )

    v2_dispatch_parser = subparsers.add_parser(
        "v2-dispatch-role",
        help="Mark the Orchestrator sleeping after dispatching one V2 role turn.",
    )
    v2_dispatch_parser.add_argument("--state", required=True)
    v2_dispatch_parser.add_argument(
        "--role",
        choices=["planner", "developer", "test", "auditor"],
        required=True,
    )
    v2_dispatch_parser.add_argument("--thread-id", required=True)
    v2_dispatch_parser.add_argument(
        "--host",
        choices=["codex", "claude-code-broker"],
        default="codex",
    )

    v2_signal_parser = subparsers.add_parser(
        "v2-return-signal",
        help="Record a V2 role return signal and print next routing.",
    )
    v2_signal_parser.add_argument("--state", required=True)
    v2_signal_parser.add_argument("--signal-json", default=None)
    v2_signal_parser.add_argument("--signal-text", default=None)

    claude_broker_parser = subparsers.add_parser(
        "claude-code-broker",
        help="Install or run the Claude Code hook-backed V2 broker.",
    )
    claude_broker_parser.add_argument("broker_args", nargs=argparse.REMAINDER)

    subparsers.add_parser(
        "mcp-serve",
        help="Run the arcgentic MCP server (stdio) exposing the round-status panel.",
    )

    args = parser.parse_args(argv)

    if args.command == "plan-round-impl":
        from .skills_impl.plan_round import run

        plan_result = run(
            round_name=args.round_name,
            round_type=args.round_type,
            prior_round_anchor=args.prior_round_anchor,
            scope_description=args.scope_description,
        )
        print(plan_result.summary())
        return plan_result.exit_code

    elif args.command == "execute-round-impl":
        from pathlib import Path as _Path

        from .skills_impl.execute_round import run as er_run

        er_result = er_run(
            round_name=args.round_name,
            handoff_path=_Path(args.handoff_path),
            dry_run=args.dry_run,
        )
        print(er_result.summary())
        return er_result.exit_code

    elif args.command == "audit-check":
        from .audit_check import main as ac_main

        extra: list[str] = []
        if args.strict:
            extra.append("--strict")
        if args.strict_extended:
            extra.append("--strict-extended")
        return ac_main([args.audit_file, *extra])

    elif args.command == "quality-gate-enforce":
        from .hooks.quality_gate_enforce import main as qg_main

        qg_extra: list[str] = []
        if args.repo_root:
            qg_extra.extend(["--repo-root", args.repo_root])
        if args.audit_handoff:
            qg_extra.extend(["--audit-handoff", args.audit_handoff])
        if args.skip_audit_check:
            qg_extra.append("--skip-audit-check")
        return qg_main(qg_extra)

    elif args.command == "validate-handoff":
        from pathlib import Path as _Path

        from .source_rules import validate_handoff_file

        handoff_result = validate_handoff_file(_Path(args.handoff_file))
        print(handoff_result.summary())
        return 0 if handoff_result.ok else 1

    elif args.command == "codify-lesson":
        from pathlib import Path as _Path

        from .skills_impl.codify_lesson import run as cl_run

        cl_result = cl_run(
            audit_dir=_Path(args.audit_dir),
            lessons_dir=_Path(args.lessons_dir),
            amendments_dir=_Path(args.amendments_dir),
            n=args.N,
            dry_run=args.dry_run,
        )
        print(cl_result.summary())
        return cl_result.exit_code

    elif args.command == "track-refs":
        from pathlib import Path as _Path

        from .skills_impl.track_refs import (
            append_to_index,
            build_reference_entry,
            emit_triplet_table,
            refresh_relevance,
            usage_evidence_from_json,
        )

        if args.track_refs_command == "refresh-relevance":
            changed = refresh_relevance(
                _Path(args.index),
                args.round_name,
                default_relevance=args.default_relevance,
            )
            print(f"track-refs refresh-relevance: {changed} blocks updated")
            return 0

        evidence = usage_evidence_from_json(args.usage_evidence)
        entry = build_reference_entry(
            repo_path=_Path(args.repo_path),
            owner_repo=args.owner_repo,
            round_name=args.round_name,
            usage_evidence=evidence,
            relevance=getattr(args, "relevance", "medium"),
        )
        if args.track_refs_command == "add":
            append_to_index(_Path(args.index), entry, args.round_name)
            print(entry.to_index_block(args.round_name))
            return 0
        if args.track_refs_command == "triplet":
            print(emit_triplet_table([entry]))
            return 0

    elif args.command == "round-boundary-lesson-scan":
        from .hooks.round_boundary_lesson_scan import main as rbls_main

        scan_extra: list[str] = [
            "--N",
            str(args.N),
            "--audit-dir",
            args.audit_dir,
            "--lessons-dir",
            args.lessons_dir,
            "--amendments-dir",
            args.amendments_dir,
        ]
        if args.dry_run:
            scan_extra.append("--dry-run")
        return rbls_main(scan_extra)

    elif args.command == "cross-session-handoff":
        from pathlib import Path as _Path

        from .skills_impl.cross_session_handoff import (
            acquire_lock,
            parse_updates_json,
            read_state,
            release_lock,
            snapshot_state,
            write_state,
        )

        state_path = _Path(args.state)
        if args.cross_command == "read":
            cross_result = read_state(state_path)
        elif args.cross_command == "write":
            cross_result = write_state(
                state_path,
                session_id=args.session_id,
                updates=parse_updates_json(args.updates),
                ttl=args.ttl,
            )
        elif args.cross_command == "snapshot":
            cross_result = snapshot_state(
                state_path,
                session_id=args.session_id,
                history_dir=_Path(args.history_dir) if args.history_dir else None,
                ttl=args.ttl,
            )
        elif args.cross_command == "acquire-lock":
            cross_result = acquire_lock(state_path, args.session_id, ttl=args.ttl)
        else:
            cross_result = release_lock(state_path, args.session_id)

        print(cross_result.message)
        if cross_result.state is not None:
            import yaml as _yaml  # type: ignore[import-untyped]

            print(_yaml.safe_dump(cross_result.state, sort_keys=False).strip())
        return cross_result.exit_code

    elif args.command == "session-mode":
        from pathlib import Path as _Path

        from .session_mode import (
            generate_identity_prompts,
            input_from_handoff,
            recommend_session_mode,
            recommend_v2_mode_from_idea,
        )

        if args.session_command == "recommend":
            handoff_path = _Path(args.handoff)
            inputs = input_from_handoff(
                round_id=args.round_name,
                handoff_text=handoff_path.read_text(encoding="utf-8"),
                handoff_path=str(handoff_path),
                dispatch_available=not args.dispatch_unavailable,
            )
            print(json.dumps(recommend_session_mode(inputs).to_dict(), indent=2, sort_keys=True))
            return 0
        if args.session_command == "recommend-v2":
            print(
                json.dumps(
                    recommend_v2_mode_from_idea(args.idea).to_dict(),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        handoff_path = _Path(args.handoff)
        prompts = generate_identity_prompts(
            round_id=args.round_name,
            handoff_path=str(handoff_path),
            candidate_roles=("developer", "auditor"),
        )
        print(prompts[args.role])
        return 0

    elif args.command == "orchestrator-dispatch":
        from pathlib import Path as _Path

        from .orchestrator_dispatch import build_dispatch_order

        dispatch = build_dispatch_order(
            round_id=args.round_name,
            handoff_path=_Path(args.handoff),
            mode=args.mode,
        )
        print(json.dumps(dispatch.to_dict(), indent=2, sort_keys=True))
        return 0

    elif args.command == "source-intake":
        from pathlib import Path as _Path

        from .source_intake import load_source_records

        records = load_source_records([_Path(path) for path in args.records])
        print(
            json.dumps(
                {"records": [record.__dict__ for record in records]},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    elif args.command == "capability-registry":
        from pathlib import Path as _Path

        from .capability_registry import build_registry

        registry = build_registry([_Path(path) for path in args.catalogs])
        output = registry.to_json()
        if args.output:
            _Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0

    elif args.command == "spec-governance":
        from pathlib import Path as _Path

        from .spec_governance import load_artifact_graph

        graph = load_artifact_graph(
            _Path(args.change_dir),
            archive_root=_Path(args.archive_root) if args.archive_root else None,
        )
        payload = {
            "archive_ready": graph.archive_ready,
            "archive_target": str(graph.archive_target),
            "completed_tasks": graph.completed_tasks,
            "delta_specs": list(graph.delta_specs),
            "errors": list(graph.errors),
            "incomplete_tasks": graph.incomplete_tasks,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if graph.archive_ready or args.spec_command == "status" else 1

    elif args.command == "agency-roster":
        from pathlib import Path as _Path

        from .agency_roster import parse_agency_roster

        roles = parse_agency_roster(_Path(args.catalog_path))
        print(
            json.dumps(
                {"roles": [role.__dict__ for role in roles]},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    elif args.command == "v1-release-readiness":
        from pathlib import Path as _Path

        from .v1_release import check_v1_release_readiness

        result = check_v1_release_readiness(
            _Path(args.repo_root),
            expected_version=args.expected_version,
            local_install_path=_Path(args.local_install_path) if args.local_install_path else None,
        )
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    elif args.command == "verdict-completeness":
        from pathlib import Path as _Path

        from .verdict_completeness import validate_verdict_completeness

        verdict_result = validate_verdict_completeness(
            _Path(args.verdict_file).read_text(encoding="utf-8")
        )
        print(json.dumps(verdict_result.__dict__, indent=2, sort_keys=True))
        return 0 if verdict_result.ok else 1

    elif args.command == "close-round":
        from pathlib import Path as _Path

        from .close_round import CloseRoundError, close_round

        try:
            close_result = close_round(
                state_path=_Path(args.state_file),
                verdict_path=_Path(args.verdict),
                audit_commit=args.audit_commit,
            )
        except CloseRoundError as exc:
            print(f"close-round failed: {exc}")
            return 1
        print(close_result.message)
        return 0

    elif args.command == "v2-session-plan":
        from pathlib import Path as _Path

        from .v2_session_orchestration import (
            V2SessionOrchestrationError,
            advance_passed_round_from_project_plan,
            build_role_session_plan,
            ensure_initial_round_id,
            load_state_file,
            remember_active_user_request,
            set_v2_mode,
            write_state_file,
        )

        try:
            state_path = _Path(args.state)
            raw_state = ensure_initial_round_id(load_state_file(state_path))
            raw_state = advance_passed_round_from_project_plan(raw_state)
            if args.mode is not None:
                raw_state = set_v2_mode(raw_state, args.host, args.mode)
            session_plan = build_role_session_plan(
                raw_state, host=args.host, user_request=args.user_request
            )
            current_round = raw_state.get("current_round")
            current_state = (
                str(current_round.get("state") or "")
                if isinstance(current_round, dict)
                else ""
            )
            if args.user_request.strip() and (
                current_state != "closed" or session_plan.actions
            ):
                raw_state = remember_active_user_request(
                    raw_state, args.user_request, host=args.host
                )
                if current_state == "closed" and session_plan.actions:
                    project = raw_state.get("project")
                    v2 = (
                        project.get("arcgentic_v2")
                        if isinstance(project, dict)
                        else None
                    )
                    if isinstance(v2, dict):
                        v2["orchestrator_status"] = "active"
            write_state_file(state_path, raw_state)
        except V2SessionOrchestrationError as exc:
            print(f"v2-session-plan failed: {exc}")
            return 1
        print(json.dumps(session_plan.to_dict(), indent=2, sort_keys=True))
        return 0

    elif args.command == "v2-record-session":
        from pathlib import Path as _Path

        from .v2_session_orchestration import (
            load_state_file,
            record_role_session,
            write_state_file,
        )

        state_path = _Path(args.state)
        try:
            updated_state = record_role_session(
                load_state_file(state_path),
                args.role,
                thread_id=args.thread_id,
                title=args.title,
                host=args.host,
                repair_current_orchestrator=args.repair_current_orchestrator,
            )
        except ValueError as exc:
            print(f"v2-record-session failed: {exc}")
            return 1
        write_state_file(state_path, updated_state)
        print(json.dumps({"recorded": True, "role": args.role, "thread_id": args.thread_id}))
        return 0

    elif args.command == "v2-dispatch-role":
        from pathlib import Path as _Path

        from .v2_session_orchestration import (
            V2SessionOrchestrationError,
            load_state_file,
            record_role_dispatch,
            write_state_file,
        )

        state_path = _Path(args.state)
        try:
            updated_state = record_role_dispatch(
                load_state_file(state_path),
                args.role,
                thread_id=args.thread_id,
                host=args.host,
            )
        except V2SessionOrchestrationError as exc:
            print(f"v2-dispatch-role failed: {exc}")
            return 1
        write_state_file(state_path, updated_state)
        print(
            json.dumps(
                {
                    "dispatched": True,
                    "orchestrator_status": "sleeping",
                    "pending_role": args.role,
                    "thread_id": args.thread_id,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    elif args.command == "v2-return-signal":
        from pathlib import Path as _Path

        from .v2_session_orchestration import (
            RoleReturnSignal,
            V2SessionOrchestrationError,
            apply_role_return_signal,
            load_state_file,
            write_state_file,
        )

        state_path = _Path(args.state)
        try:
            if bool(args.signal_json) == bool(args.signal_text):
                raise V2SessionOrchestrationError(
                    "provide exactly one of --signal-json or --signal-text"
                )
            signal = (
                RoleReturnSignal.from_json(args.signal_json)
                if args.signal_json
                else RoleReturnSignal.from_text(args.signal_text)
            )
            raw_state = load_state_file(state_path)
            if (
                signal.role == "auditor"
                and signal.state == "passed"
                and signal.status.upper() == "PASS"
            ):
                from .audit_check import run as audit_check_run

                verdict_raw = signal.artifacts.get("verdict")
                if not isinstance(verdict_raw, str) or not verdict_raw.strip():
                    raise V2SessionOrchestrationError(
                        "auditor PASS return must include artifacts.verdict"
                    )
                project = raw_state.get("project")
                project_root_raw = (
                    project.get("root") if isinstance(project, dict) else None
                )
                project_root = (
                    _Path(str(project_root_raw))
                    if project_root_raw
                    else state_path.parent.parent
                )
                verdict_path = _Path(verdict_raw)
                if not verdict_path.is_absolute():
                    verdict_path = project_root / verdict_path
                audit_check = audit_check_run(
                    verdict_path,
                    strict=True,
                    strict_extended=True,
                    repo_root=project_root,
                )
                if audit_check.exit_code != 0:
                    raise V2SessionOrchestrationError(
                        "auditor PASS strict audit-check failed: "
                        f"{audit_check.summary_text}"
                    )
            updated_state = apply_role_return_signal(raw_state, signal)
        except (json.JSONDecodeError, V2SessionOrchestrationError) as exc:
            print(f"v2-return-signal failed: {exc}")
            return 1
        write_state_file(state_path, updated_state)
        project = updated_state.get("project")
        v2 = project.get("arcgentic_v2") if isinstance(project, dict) else {}
        next_role = v2.get("next_role") if isinstance(v2, dict) else None
        print(json.dumps({"recorded": True, "next_role": next_role}, indent=2, sort_keys=True))
        return 0

    elif args.command == "claude-code-broker":
        from .claude_code_broker import main as broker_main

        return broker_main(args.broker_args)

    elif args.command == "mcp-serve":
        from .mcp.server import run_server

        run_server()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
