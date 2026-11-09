"""Alert rules for the loop itself. PAGE = an on-call engineer must act now and the message says where to look;
TICKET = review in the morning. Alerts are deduplicated by key, stored in `alerts`, logged, and served at /alerts."""
import json


class Alerts:
    CREDITS_PAGE = 0.15
    ROTATION_MIN = 120          # sim minutes a flagged caller ID may keep >5% of traffic
    HALLUC_MIN = 240            # sim minutes a hallucination incident may stay unresolved
    INGEST_WALL_S = 600         # wall seconds spent ingesting one tick

    def __init__(self, ctl):
        self.c = ctl

    def _active(self):
        return {r[0] for r in self.c.s.q("SELECT key FROM alerts WHERE cleared_ts IS NULL")}

    def evaluate(self):
        c = self.c
        want = {}
        if c.credits is not None and c.credit_total and c.credits < self.CREDITS_PAGE * c.credit_total:
            want["credits_low"] = ("-", "page", f"credits {c.credits:.0f}/{c.credit_total:.0f}: only incident validation should spend "
                                   "now; check `credits` table for the workflow burning them")
        if c.stats["decision_lag_s"] > self.INGEST_WALL_S:
            want["ingest_lag"] = ("-", "page", f"ingest of one tick took {c.stats['decision_lag_s']:.0f}s: decisions are stale; "
                                  "check events/s in /metrics and shard by workflow")
        recent_err = c.s.q("SELECT COUNT(*) FROM decisions WHERE type='controller_error' AND id > (SELECT COALESCE(MAX(id),0)-200 FROM decisions)")[0][0]
        if recent_err >= 3:
            want["controller_errors"] = ("-", "page", f"{recent_err} controller_error decisions in the last 200 records: see decisions "
                                         "where type='controller_error'")
        for wf in c.wfs.values():
            st = wf.state
            for d, f in (st.get("did_flagged") or {}).items():
                share = (wf.did_dist() or {}).get(d, 0)
                if c.minute - f["minute"] > self.ROTATION_MIN and share > 0.05:
                    want[f"did_unrotated:{wf.id}:{d}"] = (wf.id, "page", f"{wf.id}: caller ID {d} flagged {c.minute - f['minute']} min ago "
                                                          f"still carries {share:.0%} of traffic; check proposals for status refused/pending")
            inc = st.get("incident_h")
            if inc and inc.get("step") != "resolved" and c.minute - inc["detected_minute"] > self.HALLUC_MIN:
                want[f"halluc_unresolved:{wf.id}"] = (wf.id, "page", f"{wf.id}: hallucination incident open {c.minute - inc['detected_minute']} "
                                                      f"min (step {inc['step']}); check the approval for the prompt fix")
            if st.get("rejected_streak", 0) >= 3:
                want[f"rejections:{wf.id}"] = (wf.id, "ticket", f"{wf.id}: 3 consecutive proposals rejected/expired; review rationale quality")
        active = self._active()
        for k, (wf, sev, msg) in want.items():
            if k not in active:
                c.s.x("INSERT OR REPLACE INTO alerts VALUES(?,?,?,?,?,NULL)", (k, wf, sev, msg, c.now))
                c.log(f"[ALERT {sev.upper()}] {msg}")
        for k in active - set(want):
            c.s.x("UPDATE alerts SET cleared_ts=? WHERE key=?", (c.now, k))
