"""Governance client: proposal lifecycle, idempotent submit/apply, auto-apply within policy, crash reconciliation.

Our proposal status machine (stored in `proposals.status`):

  intent ──POST ok──▶ pending ──approved──▶ approved ──apply ok──▶ applied
     │                  │  ├─rejected ─▶ rejected          │ ├─410 apply window──▶ lapsed
     │                  │  └─expired  ─▶ expired           │ └─409 stale base ───▶ stale
     └─409 stale base─▶ stale                              └ (re-proposal is created by the optimiser, never by replay)
  auto path: intent ──PUT ok──▶ applied    |  403 not permitted ─▶ refused (policy)

`intent` rows are written BEFORE the external call; proposal_id is deterministic from (wf, base_version, config hash,
attempt), so replaying a crashed submit hits 409 duplicate_proposal_id and we adopt the existing approval.
"""
import hashlib
import json

from .api import ApiError

import os


def failpoint(name):
    """Crash-test hook: CTL_FAILPOINT=<name> kills the process (like SIGKILL) the first time that point is reached."""
    if os.environ.get("CTL_FAILPOINT") == name:
        os._exit(137)


TERMINAL = {"applied", "rejected", "expired", "lapsed", "stale", "refused", "failed"}


def chash(cfg):
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:8]


class Gov:
    def __init__(self, store, api, log=print):
        self.s, self.api, self.log = store, api, log

    # ------------------------------------------------------------------ queries
    def active(self, wf, kinds=None):
        rows = self.s.q("SELECT proposal_id,kind,status,approval_id,base_version,created_ts,submitted_ts FROM proposals "
                        "WHERE wf=? AND status IN ('intent','pending','approved','applying')", (wf,))
        return [r for r in rows if not kinds or r[1] in kinds]

    def submitted_since(self, wf, since_ts):
        return self.s.q("SELECT COUNT(*) FROM proposals WHERE wf=? AND via='approval' AND submitted_ts>=?", (wf, since_ts))[0][0]

    def new_id(self, wf, base_version, cfg, kind):
        h = chash(cfg)
        n = self.s.q("SELECT COUNT(*) FROM proposals WHERE wf=? AND base_version=? AND proposal_id LIKE ?",
                     (wf, base_version, f"{wf}-v{base_version}-{h}%"))[0][0]
        return f"{wf}-v{base_version}-{h}-{n}"

    # ------------------------------------------------------------------ approval path
    def submit(self, now, wf, kind, base_version, cfg, body, supersedes=None):
        """body: change_summary, diff, affected_leads, dry_run, impact_score, rationale, evidence?, expires_in_hours?"""
        pid = self.new_id(wf, base_version, cfg, kind)
        payload = {"proposal_id": pid, "workflow_id": wf, "base_version": base_version, "proposed_config": cfg, **body}
        self.s.x("INSERT INTO proposals(proposal_id,wf,kind,status,base_version,created_ts,config,body,via,supersedes) "
                 "VALUES(?,?,?,?,?,?,?,?,?,?)", (pid, wf, kind, "intent", base_version, now, json.dumps(cfg), json.dumps(body, default=str),
                                                  "approval", supersedes))
        self.s.decide(now, wf, "proposal_created", kind, body["change_summary"],
                      {"proposal_id": pid, "impact_score": body["impact_score"], "affected_leads": body["affected_leads"],
                       "diff": body["diff"], "dry_run": body["dry_run"], "rationale": body["rationale"],
                       "evidence": body.get("evidence")}, pid, base_version)
        return self._post(now, pid, payload)

    def _post(self, now, pid, payload):
        try:
            r = self.api.post("/approvals", payload)
            failpoint("after_submit_post")        # approval exists at the sim, not yet recorded here
            self.s.x("UPDATE proposals SET status='pending', approval_id=?, submitted_ts=? WHERE proposal_id=?",
                     (r["approval_id"], now, pid))
            self.s.decide(now, payload["workflow_id"], "proposal_submitted", pid, f"approval {r['approval_id']} pending",
                          {"approval": r}, pid)
            return pid
        except ApiError as e:
            if e.status == 409 and "duplicate" in json.dumps(e.body):
                for a in self.api.get("/approvals", workflow_id=payload["workflow_id"]):
                    if a.get("proposal_id") == pid:
                        self.s.x("UPDATE proposals SET status='pending', approval_id=?, submitted_ts=? WHERE proposal_id=?",
                                 (a["approval_id"], a.get("submitted_at") or a.get("created_at") or now, pid))
                        self.s.decide(now, payload["workflow_id"], "proposal_adopted", pid, "recovered after crash", {"approval": a}, pid)
                        return pid
            status = "stale" if (e.status == 409 and "stale" in json.dumps(e.body)) else "failed"
            self.s.x("UPDATE proposals SET status=?, reasons=? WHERE proposal_id=?", (status, json.dumps(e.body), pid))
            self.s.decide(now, payload["workflow_id"], "proposal_" + status, pid, f"submit refused: {e.body}", {"error": e.body}, pid)
            return None

    def reconcile(self, now, wf, current_version):
        """Poll every in-flight proposal for this workflow; apply approved ones; return list of state transitions."""
        events = []
        for pid, kind, status, aid, base, created, sub in self.s.q(
                "SELECT proposal_id,kind,status,approval_id,base_version,created_ts,submitted_ts FROM proposals "
                "WHERE wf=? AND status IN ('intent','pending','approved','applying')", (wf,)):
            if status == "intent":
                # crashed between intent and POST completing: replay (idempotent via proposal_id)
                row = self.s.q("SELECT config,body FROM proposals WHERE proposal_id=?", (pid,))[0]
                payload = {"proposal_id": pid, "workflow_id": wf, "base_version": base, "proposed_config": json.loads(row[0]),
                           **json.loads(row[1])}
                self._post(now, pid, payload)
                continue
            try:
                a = self.api.get(f"/approvals/{aid}")
            except ApiError as e:
                self.log(f"[gov] cannot read approval {aid}: {e}")
                continue
            st = a["status"]
            if st == "pending":
                continue
            if st in ("rejected", "expired", "lapsed"):
                self.s.x("UPDATE proposals SET status=?, decided_ts=?, reasons=? WHERE proposal_id=?",
                         (st, now, json.dumps(a.get("reasons") or a.get("reason") or []), pid))
                self.s.decide(now, wf, f"proposal_{st}", pid, f"{kind} proposal {st}", {"approval": a}, pid)
                events.append((pid, kind, st))
            elif st == "applied":
                self.s.x("UPDATE proposals SET status='applied' WHERE proposal_id=? AND status!='applied'", (pid,))
                events.append((pid, kind, "applied"))
            elif st == "approved":
                if status == "pending":
                    self.s.x("UPDATE proposals SET status='approved', decided_ts=? WHERE proposal_id=?", (now, pid))
                    self.s.decide(now, wf, "proposal_approved", pid, f"{kind} proposal approved by client approver",
                                  {"approval": a}, pid)
                if base != current_version:
                    self.s.x("UPDATE proposals SET status='stale' WHERE proposal_id=?", (pid,))
                    self.s.decide(now, wf, "proposal_stale", pid, f"config moved v{base}->v{current_version} (supervisor edit?) "
                                  "before apply; will re-propose from fresh data", {"base": base, "current": current_version}, pid)
                    events.append((pid, kind, "stale"))
                    continue
                self.s.x("UPDATE proposals SET status='applying' WHERE proposal_id=?", (pid,))
                try:
                    r = self.api.post(f"/workflows/{wf}/apply", {"approval_id": aid})
                    failpoint("after_apply_post")     # applied at the sim, not yet recorded here
                    ver = r.get("version") or r.get("new_version") or (r.get("config") or {}).get("version")
                    self.s.x("UPDATE proposals SET status='applied', applied_ts=?, applied_version=? WHERE proposal_id=?",
                             (now, ver, pid))
                    self.s.decide(now, wf, "proposal_applied", pid, f"{kind} applied as config v{ver}", {"result": r}, pid, ver)
                    events.append((pid, kind, "applied"))
                except ApiError as e:
                    blob = json.dumps(e.body)
                    new = "lapsed" if e.status == 410 else ("stale" if "stale" in blob else "failed")
                    self.s.x("UPDATE proposals SET status=? , reasons=? WHERE proposal_id=?", (new, blob, pid))
                    self.s.decide(now, wf, f"proposal_{new}", pid, f"apply failed: {blob}", {"error": e.body}, pid)
                    events.append((pid, kind, new))
        return events

    # ------------------------------------------------------------------ auto-apply path
    def auto_apply(self, now, wf, kind, base_version, cfg, rationale, summary, evidence=None, diff=None):
        pid = self.new_id(wf, base_version, cfg, kind)
        self.s.x("INSERT INTO proposals(proposal_id,wf,kind,status,base_version,created_ts,config,body,via) VALUES(?,?,?,?,?,?,?,?,?)",
                 (pid, wf, kind, "intent", base_version, now, json.dumps(cfg),
                  json.dumps({"change_summary": summary, "rationale": rationale, "diff": diff, "evidence": evidence}, default=str), "auto"))
        body = {"proposal_id": pid, "base_version": base_version, "proposed_config": cfg, "rationale": rationale}
        if evidence:
            body["evidence"] = evidence
        try:
            r = self.api.put(f"/workflows/{wf}/config", body)
            failpoint("after_auto_put")           # auto-applied at the sim, not yet recorded here
            ver = r.get("version") or r.get("new_version")
            self.s.x("UPDATE proposals SET status='applied', applied_ts=?, applied_version=?, submitted_ts=? WHERE proposal_id=?",
                     (now, ver, now, pid))
            self.s.decide(now, wf, "auto_applied", kind, summary, {"proposal_id": pid, "rationale": rationale, "diff": diff,
                                                                    "result": r}, pid, ver)
            return True, r
        except ApiError as e:
            if e.status == 409 and "duplicate" in json.dumps(e.body):
                self.s.x("UPDATE proposals SET status='applied', applied_ts=? WHERE proposal_id=?", (now, pid))
                return True, {}
            new = "refused" if e.status == 403 else ("stale" if "stale" in json.dumps(e.body) else "failed")
            self.s.x("UPDATE proposals SET status=?, reasons=? WHERE proposal_id=?", (new, json.dumps(e.body), pid))
            self.s.decide(now, wf, f"auto_apply_{new}", kind, f"auto-apply not accepted: {e.body}", {"error": e.body}, pid)
            return False, e.body

    def recover_auto_intents(self, now, wf, current_version):
        """After a crash an auto-apply may have succeeded without being recorded: check config history."""
        rows = self.s.q("SELECT proposal_id FROM proposals WHERE wf=? AND via='auto' AND status='intent'", (wf,))
        if not rows:
            return
        hist = {h.get("proposal_id"): h for h in self.api.get(f"/workflows/{wf}/config/history")}
        for (pid,) in rows:
            if pid in hist:
                self.s.x("UPDATE proposals SET status='applied', applied_ts=?, applied_version=? WHERE proposal_id=?",
                         (now, hist[pid]["version"], pid))
                self.s.decide(now, wf, "auto_applied", "recovered", "auto-apply confirmed from config history after restart",
                              {"proposal_id": pid}, pid, hist[pid]["version"])
            else:
                self.s.x("UPDATE proposals SET status='failed', reasons='crashed before PUT' WHERE proposal_id=?", (pid,))
