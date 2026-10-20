#!/usr/bin/env bash
# Adapter self-test: registers a throwaway handle and checks it can receive a message to itself.
# Usage: RELAY_DIR=../agentrelay-relay RELAY_URL=https://relay.greybeardconsortium.com bash test.sh
set -euo pipefail
RELAY_DIR="${RELAY_DIR:-../agentrelay-relay}"; RELAY_URL="${RELAY_URL:-https://relay.greybeardconsortium.com}"
H="adaptertest-$RANDOM$RANDOM"
export HOME="$(mktemp -d)"; trap 'rm -rf "$HOME"' EXIT
node "$RELAY_DIR/relay.js" init "$H" --url "$RELAY_URL" >/dev/null
node "$RELAY_DIR/relay.js" --as "$H" send "$H" "adapter self-test" >/dev/null
node "$RELAY_DIR/relay.js" --as "$H" poll | grep -q "adapter self-test" && echo "PASS ($H)" || { echo FAIL; exit 1; }
