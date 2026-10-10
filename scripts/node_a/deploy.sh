#!/usr/bin/env bash
# Usage: ./deploy.sh

set -euo pipefail

HOST="concur"
REMOTE_DIR="~/ArduinoApps/concur"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ssh "$HOST" "arduino-app-cli app stop $REMOTE_DIR 2>/dev/null; rm -rf $REMOTE_DIR"
scp -r "$SCRIPT_DIR/node_a_cam" "$HOST:$REMOTE_DIR"
scp -r "$SCRIPT_DIR/lib/"* "$HOST:$REMOTE_DIR/python"
scp "$SCRIPT_DIR/lib/.env" "$HOST:$REMOTE_DIR/python/.env"
ssh "$HOST" "arduino-app-cli app start $REMOTE_DIR"
