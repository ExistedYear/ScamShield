#!/usr/bin/env sh
set -eu

HOST="${SCAMSHIELD_HOST:-127.0.0.1}"
PORT="${SCAMSHIELD_PORT:-5000}"
INSTALL=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --install)
      INSTALL=1
      shift
      ;;
    -h|--help)
      echo "Usage: ./run_api.sh [--host 127.0.0.1] [--port 5000] [--install]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: ./run_api.sh [--host 127.0.0.1] [--port 5000] [--install]" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
API_ROOT="$SCRIPT_DIR/smishing_detector"

if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
  PYTHON="$SCRIPT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  PYTHON="python"
fi

if [ "$INSTALL" -eq 1 ]; then
  "$PYTHON" -m pip install -r "$API_ROOT/requirements.txt"
fi

export SCAMSHIELD_HOST="$HOST"
export SCAMSHIELD_PORT="$PORT"
export SCAMSHIELD_DEBUG="${SCAMSHIELD_DEBUG:-false}"

echo "Starting ScamShield Flask API at http://$HOST:$PORT"
echo "Health check: http://$HOST:$PORT/health"
cd "$API_ROOT"
exec "$PYTHON" -m app.flask_api
