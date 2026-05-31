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

CLI is the bridge between markdown skills (which shell out via Claude Code's
Bash tool) and the Python toolkit (which holds the actual algorithms).
"""

from __future__ import annotations

import argparse
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
