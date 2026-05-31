# arcgentic

Python CLI for the `arcgentic` Claude Code / Codex plugin.

`arcgentic` turns round-driven engineering discipline into mechanical checks:
handoff validation, execute-round self-audit, external audit fact checks,
cross-session handoff utilities, reference tracking, and lesson codification.

The package is the CLI surface of the hybrid monorepo. The plugin surface lives
at repo root (`skills/`, `agents/`, `hooks/`, `.claude-plugin/`, `.codex-plugin/`);
this package provides the Python implementation those skills shell out to.

## Install

Requires Python 3.13+.

```bash
pipx install arcgentic

# or
uv tool install arcgentic

arcgentic --help
```

## Install from source

```bash
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic/toolkit
python3 -m pip install -e ".[dev]"
arcgentic --help
```

## CLI commands

### Round implementation helpers

```bash
arcgentic plan-round-impl --round R1.0 --type substrate-touching --anchor <sha40>
arcgentic execute-round-impl --round R1.0 --handoff docs/superpowers/plans/R1.0.md
```

### Audit and gate checks

```bash
arcgentic audit-check docs/audits/R1.0.md --strict-extended
arcgentic quality-gate-enforce --repo-root .
arcgentic validate-handoff docs/superpowers/plans/R1.0.md
```

### Lessons, references, and handoff

```bash
arcgentic codify-lesson --audit-dir docs/audits
arcgentic track-refs add references/example --owner-repo owner/repo --round R1 --usage-evidence '{"pattern_only": true}'
arcgentic cross-session-handoff read
```

## Development

```bash
cd toolkit
python3 -m pip install -e ".[dev]"
```

Run quality gates from `toolkit/`:

```bash
mypy --strict src/ tests/
pytest --tb=no
ruff check .
```

## Repository

Homepage: https://github.com/Arch1eSUN/Arcgentic

Full plugin README: https://github.com/Arch1eSUN/Arcgentic#readme

## Layout

- `src/arcgentic/adapters/` — IDE adapter Protocol + implementations
- `src/arcgentic/skills_impl/` — skill implementation backends
- `src/arcgentic/audit_check.py` — mechanical audit fact checker
- `src/arcgentic/source_rules.py` — Moirai-derived source-rule contract validators
- `src/arcgentic/utils/pattern_detection.py` — repeated audit-pattern clustering for lessons
- `src/arcgentic/cli.py` — command-line bridge for skills, gates, and validators
- `tests/unit/`, `tests/integration/` — pytest suites
