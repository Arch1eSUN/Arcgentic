"""arcgentic CLI entry point — `arcgentic <subcommand> [args]`.

Subcommands wired in this module:
- `arcgentic plan-round-impl --round=R --type=T --anchor=SHA [--scope=...]`
  → calls skills_impl.plan_round.run(...)

Future subcommands (later tasks):
- `arcgentic execute-round-impl ...` (sub-phase c)
- `arcgentic audit-check <handoff> [--strict|--strict-extended]` (d.1)

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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
