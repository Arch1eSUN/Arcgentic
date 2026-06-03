# Arcgentic Privacy Policy

Effective date: 2026-06-04

Arcgentic is a local developer workflow plugin and Python CLI for rigorous AI-assisted development rounds.

## Data collection

Arcgentic does not collect, transmit, sell, or share personal data.

The core plugin and CLI do not call external analytics services, hosted AI APIs, telemetry endpoints, advertising networks, or tracking services.

## Local workflow artifacts

Arcgentic may create or update repo-local workflow artifacts when a user or coding agent runs its skills, scripts, or CLI commands. These artifacts can include:

- `.agentic-rounds/state.yaml`
- planning handoff documents
- self-audit and external-audit documents
- reference indexes
- lesson and mandate files
- command output captured by the active coding session

These files stay in the user's local repository unless the user chooses to commit, push, share, or publish them.

## Credentials and secrets

Arcgentic does not read credential stores, keychains, password managers, browser profiles, OAuth tokens, API keys, `.env` files, or other secrets as part of its core workflow.

Users should not place secrets in Arcgentic handoffs, audit documents, state files, or lessons.

## External services

Arcgentic does not require external service credentials for core use.

It does not make paid API calls to OpenAI, Anthropic, Google, Cohere, embedding providers, rerankers, vector stores, or similar AI services. Any LLM reasoning happens in the user's active coding-agent session, under that product's own terms and privacy controls.

## Background processing

Arcgentic does not run background daemons, scheduled jobs, telemetry collectors, or automatic cloud synchronization.

Commands run foreground and on demand.

## Repository and package distribution

Arcgentic is distributed through public developer surfaces such as GitHub, PyPI, Claude Code plugin manifests, Codex plugin manifests, and OpenClaw manifests. Installing Arcgentic from those services is subject to the privacy policies and terms of the relevant service.

## Contact

For privacy questions or removal requests related to Arcgentic, open an issue at:

https://github.com/Arch1eSUN/Arcgentic/issues
