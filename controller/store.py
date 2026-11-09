"""SQLite state store. One file holds everything the controller knows: ingestion cursor + aggregates, config
history, proposals, the decision/audit log, incidents and per-workflow learning state.

Crash safety: every ingest batch commits its aggregates *and* the chunk cursor in one transaction, so a chunk is
applied exactly once. Side effects on the simulator (POST /approvals, apply, PUT config) are preceded by a durable
'intent' row and are idempotent by proposal_id, so restart reconciles instead of repeating.
"""
import json
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS lead(lead_id TEXT PRIMARY KEY, wf TEXT, day INT, cell TEXT) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS lead_by_day ON lead(day);
-- segment x variant outcomes by 6h bucket and config version (experiments, drift, cohort KPIs)
CREATE TABLE IF NOT EXISTS agg_var(wf TEXT, tb INT, ver INT, cell TEXT, w TEXT, v TEXT, p TEXT,
  dials INT, conn INT, eng INT, PRIMARY KEY(wf,tb,ver,cell,w,v,p)) WITHOUT ROWID;
-- segment x hour pickup (call-time optimisation)
CREATE TABLE IF NOT EXISTS agg_hour(wf TEXT, day INT, hour INT, cell TEXT, dials INT, conn INT, eng INT,
  PRIMARY KEY(wf,day,hour,cell)) WITHOUT ROWID;
-- caller-ID health by hour bucket
CREATE TABLE IF NOT EXISTS agg_did(wf TEXT, hb INT, did TEXT, dials INT, conn INT, PRIMARY KEY(wf,hb,did)) WITHOUT ROWID;
-- prompt quality by hour bucket
CREATE TABLE IF NOT EXISTS agg_prompt(wf TEXT, hb INT, p TEXT, dials INT, conn INT, eng INT, halluc INT, flow REAL,
  PRIMARY KEY(wf,hb,p)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS lead_day(wf TEXT, day INT, cell TEXT, n INT, PRIMARY KEY(wf,day,cell)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS config_hist(wf TEXT, version INT, ts TEXT, actor TEXT, changed_dims TEXT,
  proposal_id TEXT, approval_id TEXT, config TEXT, PRIMARY KEY(wf,version)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS proposals(proposal_id TEXT PRIMARY KEY, wf TEXT, kind TEXT, status TEXT, approval_id TEXT,
  base_version INT, created_ts TEXT, submitted_ts TEXT, decided_ts TEXT, applied_ts TEXT, applied_version INT,
  config TEXT, body TEXT, reasons TEXT, via TEXT, supersedes TEXT) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, wf TEXT, type TEXT,
  subject TEXT, summary TEXT, evidence TEXT, proposal_id TEXT, config_version INT);
CREATE INDEX IF NOT EXISTS dec_wf ON decisions(wf, id);
CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT, wf TEXT, kind TEXT, subject TEXT,
  status TEXT, onset_ts TEXT, detected_ts TEXT, resolved_ts TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS credits(ts TEXT, wf TEXT, what TEXT, cost REAL, remaining REAL);
CREATE TABLE IF NOT EXISTS alerts(key TEXT PRIMARY KEY, wf TEXT, severity TEXT, message TEXT, opened_ts TEXT, cleared_ts TEXT);
CREATE TABLE IF NOT EXISTS metrics(ts TEXT, name TEXT, value REAL);
"""


class Store:
    def __init__(self, path):
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.lock = threading.RLock()

    # --- transactions ------------------------------------------------------------------------------
    def begin(self):
        self.db.execute("BEGIN")

    def commit(self):
        self.db.execute("COMMIT")

    def rollback(self):
        try:
            self.db.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass

    def q(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def x(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args)

    # --- kv / json state ---------------------------------------------------------------------------
    def kget(self, k, default=None):
        r = self.q("SELECT v FROM kv WHERE k=?", (k,))
        return json.loads(r[0][0]) if r else default

    def kset(self, k, v):
        self.x("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v)))

    # --- audit -------------------------------------------------------------------------------------
    def decide(self, ts, wf, typ, subject, summary, evidence=None, proposal_id=None, version=None):
        self.x("INSERT INTO decisions(ts,wf,type,subject,summary,evidence,proposal_id,config_version) VALUES(?,?,?,?,?,?,?,?)",
               (ts, wf, typ, subject, summary, json.dumps(evidence or {}, default=str), proposal_id, version))
