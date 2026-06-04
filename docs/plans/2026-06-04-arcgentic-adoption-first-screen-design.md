# Arcgentic Adoption First Screen Design

## Problem framing

Arcgentic v1.0.0 has enough workflow machinery. The next adoption constraint is not
more roles, gates, or adapters; it is the first 30 seconds of user comprehension.

The README should answer:

- What problem does Arcgentic solve?
- Who should use it?
- How do I install it?
- What is the smallest useful round?
- Where do I report friction?

## Key constraints

- Keep the value proposition compressed:
  `Arcgentic turns AI coding from ad-hoc prompting into a gated engineering workflow.`
- Do not add product functionality in this slice.
- Do not fabricate demo GIF/video assets; list them as the next adoption asset.
- Keep existing installation methods, but move the recommended path above the full matrix.
- Add feedback routes for installation failure, workflow confusion, and workflow mismatch.

## Chosen approach

Rewrite the README first screen into an adoption-oriented entry point, then add
GitHub issue templates. This gives Claude plugin library users a fast path from
interest to first round without changing Arcgentic internals.

## Out of scope

- Demo GIF/video production.
- Example project implementation.
- New CLI commands, gates, skills, agents, or hooks.
- Marketplace claim changes beyond what the current repo already documents.

## Verification

- README still links to the full install and quickstart sections.
- `.github/ISSUE_TEMPLATE/` exposes focused feedback forms.
- `git diff --stat` is limited to adoption docs and issue templates.
