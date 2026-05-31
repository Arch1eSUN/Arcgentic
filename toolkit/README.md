# arcgentic toolkit

Python CLI + adapter layer for the `arcgentic` Claude Code plugin.

This is the **toolkit surface** of the arcgentic hybrid monorepo (see
[Spec Amendment 01](../docs/plans/2026-05-13-arcgentic-v0.2.0-spec-amendment-01-layout.md)
for why). The plugin surface (`skills/`, `agents/`, `hooks/`, `.githooks/` at repo root)
provides markdown contracts discoverable by Claude Code; this toolkit provides the
Python implementation that markdown skills shell out to.

## Install (dev)

```bash
cd toolkit
pip install -e ".[dev]"
arcgentic --help
```

## CLI commands

```bash
arcgentic plan-round-impl --round R1.0 --type substrate-touching --anchor <sha40>
arcgentic execute-round-impl --round R1.0 --handoff docs/superpowers/plans/R1.0.md
arcgentic audit-check docs/audits/R1.0.md --strict-extended
arcgentic quality-gate-enforce --repo-root .
arcgentic validate-handoff docs/superpowers/plans/R1.0.md
```

## Quality gates (run from `toolkit/`)

```bash
mypy --strict src/ tests/
pytest --tb=no
ruff check .
```

## Layout

- `src/arcgentic/adapters/` — IDE adapter Protocol + implementations
- `src/arcgentic/skills_impl/` — `plan-round` + `execute-round` implementation backends
- `src/arcgentic/audit_check.py` — mechanical audit fact checker
- `src/arcgentic/source_rules.py` — Moirai-derived source-rule contract validators
- `src/arcgentic/cli.py` — command-line bridge for skills, gates, and validators
- `tests/unit/`, `tests/integration/` — pytest suites
