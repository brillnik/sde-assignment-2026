"""Streaming, idempotent event ingestion.

Each chunk is parsed once, folded into compact aggregates in memory, and flushed to SQLite in a single
transaction together with the chunk cursor. Raw events are never stored (at 850k events/day that would be the
first thing to break); everything detection/experiments need is an aggregate keyed by cohort-able segment cells.
"""
import datetime as dt
import json
import time

FEATURES = ("lang", "city_tier", "age_band", "value_band")
BASE = dt.date(2027, 1, 4).toordinal()
_day_cache = {}


def day_of(ts):
    d = ts[:10]
    v = _day_cache.get(d)
    if v is None:
        v = dt.date.fromisoformat(d).toordinal() - BASE
        _day_cache[d] = v
    return v


def minute_of_day(ts):
    return int(ts[11:13]) * 60 + int(ts[14:16])


def cell_of(features):
    return "|".join(str(features.get(f, "?")) for f in FEATURES)


def cell_features(cell):
    return dict(zip(FEATURES, cell.split("|")))


class Ingestor:
    KEEP_LEAD_DAYS = 6

    def __init__(self, store, api, log=print):
        self.s, self.api, self.log = store, api, log
        self.leads = {}
        for lid, cell in store.q("SELECT lead_id, cell FROM lead"):
            self.leads[lid] = cell
        self.last_event_id = store.kget("last_event_id", 0)
        self.total_events = store.kget("total_events", 0)

    # ------------------------------------------------------------------------------------------------
    def pending_chunks(self, kind):
        cur = self.s.kget(f"cursor:{kind}", -1)
        return [c for c in self.api.get("/events/chunks", kind=kind, after=cur)]

    def ingest_all(self, kind="events"):
        """Ingest every chunk after the cursor. Returns (control_events, n_events, seconds, latest_ts)."""
        ctrl, n, t0, latest = [], 0, time.time(), None
        for ch in self.pending_chunks(kind):
            text = self.api.text(f"/events/chunks/{ch['chunk']}")
            c, k, ts = self._ingest_chunk(kind, ch["chunk"], text)
            ctrl += c
            n += k
            latest = ts or latest
        return ctrl, n, time.time() - t0, latest

    # ------------------------------------------------------------------------------------------------
    def _ingest_chunk(self, kind, chunk_no, text):
        S = self.s
        av, ah, ad, ap, ld, newleads, ctrl = {}, {}, {}, {}, {}, [], []
        n, last_ts, loads = 0, None, json.loads
        leads = self.leads
        eid_floor = self.last_event_id if kind == "events" else S.kget("last_hist_event_id", 0)
        max_eid = eid_floor
        for line in text.splitlines():
            if not line:
                continue
            e = loads(line)
            eid = e.get("event_id", 0)
            if eid <= eid_floor:            # idempotency belt-and-braces; cursor already makes chunks exactly-once
                continue
            if eid > max_eid:
                max_eid = eid
            n += 1
            t = e["type"]
            ts = e["ts"]
            last_ts = ts
            if t == "call":
                wf = e["workflow_id"]
                day = day_of(ts)
                hour = int(ts[11:13])
                cell = leads.get(e["lead_id"], "?|?|?|?")
                var = e["variant"]
                conn = 1 if e["connected"] else 0
                eng = 1 if e.get("engaged") else 0
                k = (wf, day * 4 + hour // 6, e["config_version"], cell, var["welcome_message"], var["voice"], var["prompt_version"])
                a = av.get(k)
                if a is None:
                    av[k] = [1, conn, eng]
                else:
                    a[0] += 1; a[1] += conn; a[2] += eng
                k = (wf, day, hour, cell)
                a = ah.get(k)
                if a is None:
                    ah[k] = [1, conn, eng]
                else:
                    a[0] += 1; a[1] += conn; a[2] += eng
                hb = day * 24 + hour
                k = (wf, hb, var["caller_id"])
                a = ad.get(k)
                if a is None:
                    ad[k] = [1, conn]
                else:
                    a[0] += 1; a[1] += conn
                k = (wf, hb, var["prompt_version"])
                a = ap.get(k)
                if a is None:
                    ap[k] = [1, conn, eng, 0, 0.0]
                    a = ap[k]
                else:
                    a[0] += 1; a[1] += conn; a[2] += eng
                if conn:
                    qa = e.get("qa") or {}
                    if qa.get("hallucination_flag"):
                        a[3] += 1
                    a[4] += qa.get("flow_adherence", 0.0)
            elif t == "lead":
                cell = cell_of(e["features"])
                leads[e["lead_id"]] = cell
                day = day_of(ts)
                newleads.append((e["lead_id"], e["workflow_id"], day, cell))
                k = (e["workflow_id"], day, cell)
                ld[k] = ld.get(k, 0) + 1
            elif t in ("config_changed", "approval_decided"):
                ctrl.append(e)
        S.begin()
        try:
            S.db.executemany("INSERT OR REPLACE INTO lead(lead_id,wf,day,cell) VALUES(?,?,?,?)", newleads)
            S.db.executemany(
                "INSERT INTO lead_day(wf,day,cell,n) VALUES(?,?,?,?) ON CONFLICT(wf,day,cell) DO UPDATE SET n=n+excluded.n",
                [(*k, v) for k, v in ld.items()])
            S.db.executemany(
                "INSERT INTO agg_var VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(wf,tb,ver,cell,w,v,p) DO UPDATE SET "
                "dials=dials+excluded.dials, conn=conn+excluded.conn, eng=eng+excluded.eng",
                [(*k, *v) for k, v in av.items()])
            S.db.executemany(
                "INSERT INTO agg_hour VALUES(?,?,?,?,?,?,?) ON CONFLICT(wf,day,hour,cell) DO UPDATE SET "
                "dials=dials+excluded.dials, conn=conn+excluded.conn, eng=eng+excluded.eng",
                [(*k, *v) for k, v in ah.items()])
            S.db.executemany(
                "INSERT INTO agg_did VALUES(?,?,?,?,?) ON CONFLICT(wf,hb,did) DO UPDATE SET "
                "dials=dials+excluded.dials, conn=conn+excluded.conn",
                [(*k, *v) for k, v in ad.items()])
            S.db.executemany(
                "INSERT INTO agg_prompt VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(wf,hb,p) DO UPDATE SET "
                "dials=dials+excluded.dials, conn=conn+excluded.conn, eng=eng+excluded.eng, "
                "halluc=halluc+excluded.halluc, flow=flow+excluded.flow",
                [(*k, *v) for k, v in ap.items()])
            S.kset(f"cursor:{kind}", chunk_no)
            if kind == "events":
                self.last_event_id = max_eid
                self.total_events += n
                S.kset("last_event_id", max_eid)
                S.kset("total_events", self.total_events)
            else:
                S.kset("last_hist_event_id", max_eid)
            S.commit()
        except Exception:
            S.rollback()
            for lid, *_ in newleads:      # keep memory consistent with the (rolled back) DB
                leads.pop(lid, None)
            raise
        return ctrl, n, last_ts

    def prune(self, today):
        cutoff = today - self.KEEP_LEAD_DAYS
        old = [r[0] for r in self.s.q("SELECT lead_id FROM lead WHERE day<?", (cutoff,))]
        if old:
            self.s.x("DELETE FROM lead WHERE day<?", (cutoff,))
            for lid in old:
                self.leads.pop(lid, None)
