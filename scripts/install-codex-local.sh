#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-codex-local.sh [--plugin-root PATH] [--home PATH] [--skip-validate]

Install Arcgentic as a local Codex plugin source:
- creates ~/plugins/arcgentic as a symlink to the repo
- writes ~/plugins/.agents/plugins/marketplace.json
- validates the Codex plugin manifest when the validator is available
EOF
}

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_HOME="${HOME}"
SKIP_VALIDATE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --plugin-root)
      PLUGIN_ROOT="$2"
      shift 2
      ;;
    --home)
      INSTALL_HOME="$2"
      shift 2
      ;;
    --skip-validate)
      SKIP_VALIDATE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

PLUGIN_ROOT="$(cd "$PLUGIN_ROOT" && pwd)"
PLUGIN_LINK="$INSTALL_HOME/plugins/arcgentic"
MARKETPLACE_DIR="$INSTALL_HOME/plugins/.agents/plugins"
MARKETPLACE_FILE="$MARKETPLACE_DIR/marketplace.json"

if [ ! -f "$PLUGIN_ROOT/.codex-plugin/plugin.json" ]; then
  echo "Codex plugin manifest missing: $PLUGIN_ROOT/.codex-plugin/plugin.json" >&2
  exit 1
fi

mkdir -p "$INSTALL_HOME/plugins" "$MARKETPLACE_DIR"

if [ -L "$PLUGIN_LINK" ]; then
  CURRENT_TARGET="$(readlink "$PLUGIN_LINK")"
  if [ "$CURRENT_TARGET" != "$PLUGIN_ROOT" ]; then
    rm "$PLUGIN_LINK"
    ln -s "$PLUGIN_ROOT" "$PLUGIN_LINK"
  fi
elif [ -e "$PLUGIN_LINK" ]; then
  echo "Refusing to replace non-symlink path: $PLUGIN_LINK" >&2
  exit 1
else
  ln -s "$PLUGIN_ROOT" "$PLUGIN_LINK"
fi

cat > "$MARKETPLACE_FILE" <<'JSON'
{
  "name": "arc-studio-local",
  "interface": {
    "displayName": "Arc Studio Local"
  },
  "plugins": [
    {
      "name": "arcgentic",
      "source": {
        "source": "local",
        "path": "./arcgentic"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
JSON

VALIDATOR="$INSTALL_HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
if [ "$SKIP_VALIDATE" -eq 0 ] && [ -f "$VALIDATOR" ]; then
  python3 "$VALIDATOR" "$PLUGIN_LINK"
fi

echo "arcgentic Codex local plugin installed"
echo "plugin_link=$PLUGIN_LINK"
echo "marketplace=$MARKETPLACE_FILE"
