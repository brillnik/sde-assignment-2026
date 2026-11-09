#!/usr/bin/env bash
# Deterministic crash test: kill the controller exactly between a successful side effect at the simulator and its local
# record (submit, apply, auto-apply), restart, finish, and check nothing was duplicated or lost.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"; PORT=8711; SC=scenarios/public_02_incidents.yaml
[ -d runs/base_public_02 ] || $PY -m sim baseline --scenario $SC --run-dir runs/base_public_02 >/dev/null
for FP in after_submit_post after_apply_post after_auto_put; do
  echo "=== failpoint: $FP"
  DB=state/fp_$FP.db; rm -f $DB $DB-wal $DB-shm
  $PY -m sim serve --scenario $SC --run-dir runs/mine_fp --force --port $PORT >/dev/null 2>&1 & SIM=$!
  for i in $(seq 40); do curl -sf localhost:$PORT/health >/dev/null && break; sleep 1; done
  set +e; CTL_FAILPOINT=$FP CTL_DB=$DB CTL_VIEW_PORT=0 ./run.sh http://127.0.0.1:$PORT 2>/dev/null; RC=$?; set -e
  echo "controller exit code at failpoint: $RC (137 = killed there) at sim $(curl -s localhost:$PORT/sim/state | $PY -c 'import sys,json;print(json.load(sys.stdin)["ts"])')"
  CTL_DB=$DB CTL_VIEW_PORT=0 ./run.sh http://127.0.0.1:$PORT 2>/dev/null
  $PY -m sim grade --run runs/mine_fp --baseline runs/base_public_02 --out reports/fp_$FP.md >/dev/null
  $PY scripts/check_invariants.py $DB runs/mine_fp | grep -E "PASS|FAIL"
  $PY - <<PY2
import re, json, sqlite3
t = open("reports/fp_$FP.md").read()
g = json.loads(re.search(r'"approval_requests".*?\n}', "{" + t.split('"approval_requests"',1)[1].split("\`\`\`")[0], re.S).group(0).join(["{", ""]) if False else "{" + '"approval_requests"' + t.split('"approval_requests"',1)[1].split("\`\`\`")[0])
db = sqlite3.connect("$DB")
ours = db.execute("SELECT COUNT(*) FROM proposals WHERE via='approval' AND approval_id IS NOT NULL").fetchone()[0]
print(f"sim approval_requests={g['approval_requests']} ours(with approval id)={ours} apply_conflicts={g['apply_conflicts']} lapsed={g['lapsed']}")
assert g['approval_requests'] == ours, "approval count mismatch (duplicate or lost request)"
assert g['apply_conflicts'] == 0
PY2
  kill $SIM; wait $SIM 2>/dev/null || true
done
echo "ALL FAILPOINT TESTS PASSED"
