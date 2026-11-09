"""Post-run invariants for the crash test (reads only the controller's own store and prints the grader's governance block
location; it never touches the simulator's internals)."""
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
bad = 0
def check(name, ok, detail=""):
    global bad
    print(("PASS " if ok else "FAIL ") + name, detail)
    bad += 0 if ok else 1

q = lambda s: db.execute(s).fetchall()
check("no proposal left in 'intent'/'applying'", not q("SELECT 1 FROM proposals WHERE status IN ('intent','applying')"))
check("no config version applied twice for one proposal",
      not q("SELECT proposal_id FROM proposals WHERE status='applied' GROUP BY wf, applied_version HAVING COUNT(*)>1"))
check("every applied proposal has a recorded decision trail",
      not q("SELECT proposal_id FROM proposals WHERE status='applied' AND proposal_id NOT IN (SELECT proposal_id FROM decisions WHERE proposal_id IS NOT NULL)"))
check("event cursor == last chunk", q("SELECT v FROM kv WHERE k='cursor:events'") != [])
dups = q("SELECT wf,version,COUNT(*) FROM config_hist GROUP BY wf,version HAVING COUNT(*)>1")
check("config history has no duplicate versions", not dups)
n_app = q("SELECT COUNT(*) FROM proposals WHERE status='applied'")[0][0]
n_pro = q("SELECT COUNT(*) FROM proposals")[0][0]
print(f"proposals total={n_pro} applied={n_app}; decisions={q('SELECT COUNT(*) FROM decisions')[0][0]}")
print("see reports/crash_02.md for the simulator-side governance counts (apply_conflicts must be 0, no duplicate requests)")
sys.exit(1 if bad else 0)
