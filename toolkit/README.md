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
arcgentic --help  # entry point lands in later task (a.4+)
```

## Quality gates (run from `toolkit/`)

```bash
mypy --strict src/ tests/
pytest --tb=no
ruff check .
```

## Layout

- `src/arcgentic/adapters/` — IDE adapter Protocol + 5 implementations (this task ships `base.py` only)
- `src/arcgentic/` (later tasks) — `cli.py`, `audit_check.py`, `skills_impl/`
- `tests/unit/`, `tests/integration/` — pytest suites
