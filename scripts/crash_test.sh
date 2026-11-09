#!/usr/bin/env bash
# Crash-recovery demonstration: SIGKILL the controller several times at arbitrary points of public_02, restart each
# time with the same state DB, let the last one finish, then check invariants and grade the run.
#   scripts/crash_test.sh            (uses port 8702)
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"; PORT=8702; NAME=crash_02; SC=scenarios/public_02_incidents.yaml
mkdir -p logs reports
[ -d runs/base_public_02 ] || $PY -m sim baseline --scenario $SC --run-dir runs/base_public_02 >/dev/null
rm -f state/$NAME.db*
$PY -m sim serve --scenario $SC --run-dir runs/mine_$NAME --force --port $PORT >logs/sim_$NAME.log 2>&1 &
SIM=$!; trap 'kill $SIM 2>/dev/null || true' EXIT
for i in $(seq 1 60); do curl -sf localhost:$PORT/health >/dev/null && break; sleep 1; done
: > logs/ctl_$NAME.log
for delay in 3 2 4 1 5 2 3; do
  CTL_DB=state/$NAME.db CTL_VIEW_PORT=0 ./run.sh http://127.0.0.1:$PORT 2>>logs/ctl_$NAME.log &
  PID=$!
  sleep $delay
  if kill -0 $PID 2>/dev/null; then
    kill -9 $PID; wait $PID 2>/dev/null || true
    echo "killed controller after ${delay}s at sim: $(curl -s localhost:$PORT/sim/state | $PY -c 'import sys,json;print(json.load(sys.stdin)["ts"])')"
  else
    echo "controller already finished"; break
  fi
done
echo "--- final restart: runs to completion"
CTL_DB=state/$NAME.db CTL_VIEW_PORT=0 ./run.sh http://127.0.0.1:$PORT 2>>logs/ctl_$NAME.log
$PY -m sim grade --run runs/mine_$NAME --baseline runs/base_public_02 --out reports/crash_02.md >/dev/null
$PY scripts/check_invariants.py state/$NAME.db runs/mine_$NAME
