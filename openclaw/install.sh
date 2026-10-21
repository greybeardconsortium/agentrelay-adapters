#!/usr/bin/env bash
# Install the agentrelay skill into OpenClaw for one relay handle.
# usage: bash install.sh <path-to-agentrelay-relay-clone> <handle> [skills-dir (default ~/.openclaw/skills)]
set -euo pipefail
RELAY_DIR="$(cd "${1:?relay clone path}" && pwd)"; HANDLE="${2:?handle}"; DEST="${3:-$HOME/.openclaw/skills}/agentrelay"
[ -f "$RELAY_DIR/relay.js" ] || { echo "no relay.js in $RELAY_DIR"; exit 1; }
mkdir -p "$DEST"
sed -e "s#{{RELAY_DIR}}#$RELAY_DIR#g" -e "s#{{HANDLE}}#$HANDLE#g" "$(dirname "$0")/skills/agentrelay/SKILL.md" > "$DEST/SKILL.md"
echo "installed $DEST/SKILL.md for @$HANDLE (client $RELAY_DIR)"
