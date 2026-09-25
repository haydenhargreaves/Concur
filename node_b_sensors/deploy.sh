#!/usr/bin/env bash
# Redeploys node_b_sensors to the board.
#
# scp -r into an already-existing remote directory nests the source folder
# inside it (~/ArduinoApps/node_b_sensors/node_b_sensors/...) instead of
# overwriting it, so the running app keeps serving stale files. This stops
# the app, wipes the old copy, copies the current one over, and restarts it.
#
# Usage: ./deploy.sh <BOARD_IP>

set -euo pipefail

BOARD_IP="${1:?Usage: ./deploy.sh <BOARD_IP>}"
REMOTE_DIR="~/ArduinoApps/node_b_sensors"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ssh "arduino@$BOARD_IP" "arduino-app-cli app stop $REMOTE_DIR 2>/dev/null; rm -rf $REMOTE_DIR"
scp -r "$SCRIPT_DIR" "arduino@$BOARD_IP:$REMOTE_DIR"
ssh "arduino@$BOARD_IP" "arduino-app-cli app start $REMOTE_DIR"
