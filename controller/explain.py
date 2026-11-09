"""Audit queries over the controller's own store: "why did workflow X change at T, who approved it, what happened next?"

    python -m controller.explain --db state/controller.db --wf ks_cancel --at 2027-01-07T14:00:00+05:30
"""
import argparse
import json
import sqlite3


def _rows(db, sql, args=()):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def explain(db, wf, at=None, window_h=24):
    """Config versions around `at`, with the proposal that produced each, its evidence and approval decision, and what
    the audit log recorded afterwards."""
    versions = _rows(db, "SELECT version,ts,actor,changed_dims,proposal_id,approval_id FROM config_hist WHERE wf=? ORDER BY version", (wf,))
    if at:
        versions = [v for v in versions if v["ts"] <= at][-1:] + [v for v in versions if v["ts"] > at][:1]
    out = []
    for v in versions:
        item = {"config_version": v["version"], "at": v["ts"], "actor": v["actor"], "changed_dims": v["changed_dims"]}
        pid = v["proposal_id"]
        if pid:
            p = _rows(db, "SELECT * FROM proposals WHERE proposal_id=?", (pid,))
            if p:
                p = p[0]
                body = json.loads(p["body"] or "{}")
                item["proposal"] = {"id": pid, "kind": p["kind"], "via": p["via"], "status": p["status"], "approval_id": p["approval_id"],
                                    "submitted": p["submitted_ts"], "decided": p["decided_ts"], "applied": p["applied_ts"],
                                    "summary": body.get("change_summary"), "rationale": body.get("rationale"),
                                    "impact_score": body.get("impact_score"), "affected_leads": body.get("affected_leads"),
                                    "diff": body.get("diff"), "dry_run": body.get("dry_run"), "evidence": body.get("evidence")}
            item["trail"] = _rows(db, "SELECT ts,type,summary FROM decisions WHERE proposal_id=? ORDER BY id", (pid,))
        else:
            item["trail"] = _rows(db, "SELECT ts,type,summary FROM decisions WHERE wf=? AND type IN ('supervisor_edit','config_changed') "
                                      "AND config_version=? ORDER BY id", (wf, v["version"]))
        item["after"] = _rows(db, "SELECT ts,type,summary FROM decisions WHERE wf=? AND ts>? AND type NOT IN ('credit_spend') "
                                  "ORDER BY id LIMIT 8", (wf, v["ts"]))
        out.append(item)
    return out


def supervisor_view(db, wf=None):
    """Consolidated screen: what is being tested, what is winning, what we want from you, what changed today."""
    wfs = [r[0] for r in db.execute("SELECT DISTINCT wf FROM config_hist")] if not wf else [wf]
    view = {}
    for w in wfs:
        st = json.loads(db.execute("SELECT v FROM kv WHERE k=?", (f"wf:{w}",)).fetchone()[0])
        cfg = db.execute("SELECT config,version FROM config_hist WHERE wf=? AND config IS NOT NULL ORDER BY version DESC LIMIT 1", (w,)).fetchone()
        cfgj = json.loads(cfg[0]) if cfg else {}
        view[w] = {
            "config_version": cfg[1] if cfg else None,
            "prompt": cfgj.get("prompt_version"),
            "cohorts": cfgj.get("cohorts"),
            "allocations (being tested / winning)": cfgj.get("allocations"),
            "needs_your_decision": _rows(db, "SELECT proposal_id,kind,status,submitted_ts FROM proposals WHERE wf=? AND status IN ('pending','approved')", (w,)),
            "recent_proposals": _rows(db, "SELECT proposal_id,kind,status,via,submitted_ts,applied_ts FROM proposals WHERE wf=? ORDER BY created_ts DESC LIMIT 5", (w,)),
            "open_incidents": _rows(db, "SELECT kind,subject,status,detected_ts FROM incidents WHERE wf=? AND status='open'", (w,)),
            "held_after_your_edits": st.get("hold"),
            "banned_decayed_variants": st.get("bans"),
            "flagged_caller_ids": list((st.get("did_flagged") or {}).keys()),
            "latest_decisions": _rows(db, "SELECT ts,type,summary FROM decisions WHERE wf=? AND type NOT IN ('credit_spend') ORDER BY id DESC LIMIT 8", (w,)),
        }
    return view


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="state/controller.db")
    ap.add_argument("--wf", required=True)
    ap.add_argument("--at")
    a = ap.parse_args()
    db = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    print(json.dumps(explain(db, a.wf, a.at), indent=1, default=str))


if __name__ == "__main__":
    main()
