"""arcgentic CLI entry point — `arcgentic <subcommand> [args]`.

Subcommands wired in this module:
- `arcgentic plan-round-impl --round=R --type=T --anchor=SHA [--scope=...]`
  → calls skills_impl.plan_round.run(...)
- `arcgentic execute-round-impl --round=R --handoff=PATH [--dry-run]`
  → calls skills_impl.execute_round.run(...)
- `arcgentic audit-check <audit_file> [--strict|--strict-extended]`
  → calls audit_check.main(...)

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

    args = parser.parse_args(argv)

    if args.command == "plan-round-impl":
        from .skills_impl.plan_round import run

        result = run(
            round_name=args.round_name,
            round_type=args.round_type,
            prior_round_anchor=args.prior_round_anchor,
            scope_description=args.scope_description,
        )
        print(result.summary())
        return result.exit_code

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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
