#!/usr/bin/env bash
# install-hooks.sh — configure git to use the .githooks directory.
#
# Usage:
#   ./scripts/install-hooks.sh

set -euo pipefail

git config core.hooksPath .githooks
echo "Installed: git core.hooksPath = .githooks"
echo "Hooks in this directory:"
ls -la .githooks/
