# Usage: ./deploy.sh <BOARD_IP>

set -euo pipefail

BOARD_IP="${1:?Usage: ./deploy.sh <BOARD_IP>}"
REMOTE_DIR="~/ArduinoApps/node_b_sensors"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ssh "arduino@$BOARD_IP" "arduino-app-cli app stop $REMOTE_DIR 2>/dev/null; rm -rf $REMOTE_DIR"
scp -r "$SCRIPT_DIR" "arduino@$BOARD_IP:$REMOTE_DIR"
scp -r "$SCRIPT_DIR/../lib/"* "arduino@$BOARD_IP:$REMOTE_DIR/python"
ssh "arduino@$BOARD_IP" "arduino-app-cli app start $REMOTE_DIR"
