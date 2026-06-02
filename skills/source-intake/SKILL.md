---
name: source-intake
description: Use when a round cites external workflow sources, marketplace catalogs, OpenSpec resources, reference repos, or asks to fuse outside workflow material into arcgentic planning.
---

# source-intake

Records external workflow sources as auditable arcgentic inputs without vendoring their
runtime code.

## Workflow

1. Classify each source as `repo`, `marketplace`, `openspec`, or `doc`.
2. Record `id`, `origin`, `revision`, `license`, `used_parts`, `excluded_parts`, and
   `rt_tier` in YAML.
3. Validate records before planning or audit:

   ```bash
   arcgentic source-intake validate docs/source-intake/*.yaml
   ```

4. Treat RT0/RT1 sources as reference material only unless the founder explicitly approves
   a deeper integration path.

## Boundaries

- Do not fetch remote sources automatically.
- Do not install marketplace plugins.
- Do not copy third-party plugin or role code into arcgentic runtime.
