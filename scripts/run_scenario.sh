#!/usr/bin/env bash
# Usage: scripts/run_scenario.sh <scenario.yaml> <name> [port]
# Fresh baseline + fresh sim + controller via ./run.sh + grade. Writes runs/<name>, state/<name>.db, reports/<name>.md
set -euo pipefail
cd "$(dirname "$0")/.."
SC="$1"; NAME="$2"; PORT="${3:-8700}"
PY="${PYTHON:-python3}"
mkdir -p reports logs
[ -d runs/base_$NAME ] || $PY -m sim baseline --scenario "$SC" --run-dir runs/base_$NAME >/dev/null
rm -f state/$NAME.db state/$NAME.db-wal state/$NAME.db-shm
$PY -m sim serve --scenario "$SC" --run-dir runs/mine_$NAME --force --port "$PORT" >logs/sim_$NAME.log 2>&1 &
SIM=$!
trap 'kill $SIM 2>/dev/null || true' EXIT
for i in $(seq 1 60); do curl -sf localhost:$PORT/health >/dev/null && break; sleep 1; done
START=$(date +%s)
CTL_DB=state/$NAME.db ./run.sh http://127.0.0.1:$PORT 2>logs/ctl_$NAME.log
echo "controller wall time: $(( $(date +%s) - START ))s"
$PY -m sim grade --run runs/mine_$NAME --baseline runs/base_$NAME --out reports/$NAME.md >/dev/null
echo "report: reports/$NAME.md"
