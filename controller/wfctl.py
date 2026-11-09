"""Per-workflow control logic: config sync, supervisor-edit handling, caller-ID health, hallucination incident
response, winner decay/rollback, and the periodic optimiser that builds governed proposals."""
import copy
import json
import math
from collections import defaultdict

from . import detect
from .api import ApiError
from .cohorts import Cohort, assign
from .gov import chash
from .ingest import cell_features, day_of
from .planner import DIMS, Planner, kpi, norm, tv

CUSTOMER_FACING = {"welcome_message", "voice", "cohorts", "prompt_version"}
HOLD_DAYS = 2
BACKOFF_H = 12          # after a rejection/expiry wait this long before re-proposing (fresh data, fresh proposal)


def ts_parts(ts):
    d = day_of(ts)
    return d, int(ts[11:13]), int(ts[14:16])


def dist_of(cfg, cid, dim):
    a = cfg.get("allocations", {})
    return (a.get(cid, {}).get(dim)) or (a.get("default", {}).get(dim)) or {}


def changed_dims(old, new):
    out = set()
    if old.get("cohorts") != new.get("cohorts"):
        out.add("cohorts")
    if old.get("prompt_version") != new.get("prompt_version"):
        out.add("prompt_version")
    if old.get("schedule") != new.get("schedule"):
        out.add("schedule")
    oa, na = old.get("allocations", {}), new.get("allocations", {})
    for dim in ("welcome_message", "voice", "caller_id"):
        for cid in set(oa) | set(na):
            if (oa.get(cid, {}).get(dim) or {}) != (na.get(cid, {}).get(dim) or {}):
                out.add(dim)
    return out


class WF:
    def __init__(self, ctl, wf_id, info):
        self.ctl, self.id, self.info = ctl, wf_id, info
        self.s, self.api, self.gov, self.log = ctl.s, ctl.api, ctl.gov, ctl.log
        self.planner = Planner(self.s)
        self.gv = info["governance"]
        self.state = self.s.kget(f"wf:{wf_id}") or {}
        self.cfg, self.version = None, None

    # ------------------------------------------------------------------ persistence
    def save(self):
        self.s.kset(f"wf:{self.id}", self.state)

    def audit(self, typ, subject, summary, evidence=None, pid=None):
        self.s.decide(self.ctl.now, self.id, typ, subject, summary, evidence, pid, self.version)

    # ------------------------------------------------------------------ time
    @property
    def tparts(self):
        return ts_parts(self.ctl.now)

    @property
    def now_tb(self):
        d, h, _ = self.tparts
        return d * 4 + h // 6

    @property
    def now_hb(self):
        d, h, _ = self.tparts
        return d * 24 + h

    def approver_window_ok(self, urgent=False):
        d, h, m = self.tparts
        lo, hi = self.gv["approver_hours"]
        ttl = self.gv["proposal_ttl_hours"]
        lat = self.gv["approver_latency_minutes"][1] / 60.0
        if lo + 1 <= h < hi - 1 or (urgent and lo <= h < hi):
            return True
        if urgent:
            wait = (lo - h) % 24
            return wait + lat <= ttl - 1          # it would still be decided before it expires
        return False

    # ------------------------------------------------------------------ init
    def init_state(self):
        cfg = self.api.get(f"/workflows/{self.id}/config")
        self.cfg, self.version = cfg["config"], cfg["version"]
        if "ref" not in self.state:
            ref = {}
            for dim in DIMS:
                dist = dist_of(self.cfg, "default", dim)
                ref[dim] = max(dist, key=dist.get) if dist else self.info["options"][dim][0]
            self.state.update({"ref": ref, "regime_tb": -10 ** 6, "hold": {}, "bans": {}, "version": self.version,
                               "prompt_good": self.cfg.get("prompt_version"), "did_flagged": {}, "last_opt_ts": None,
                               "last_eval_day": -999, "backoff_until": None, "incident_h": None, "auto_target": None})
            self.s.x("INSERT OR REPLACE INTO config_hist VALUES(?,?,?,?,?,?,?,?)",
                     (self.id, self.version, self.ctl.now, "business_default", "[]", None, None, json.dumps(self.cfg)))
            self.audit("init", "reference", f"reference variants {ref}; prompt {self.cfg.get('prompt_version')}",
                       {"ref": ref, "config": self.cfg})
            self.save()

    # ------------------------------------------------------------------ config sync / supervisor edits
    def sync_config(self):
        cfg = self.api.get(f"/workflows/{self.id}/config")
        new_v = cfg["version"]
        if new_v != self.version or self.cfg is None:
            old_v = self.version
            self.cfg, self.version = cfg["config"], new_v
            hist = [h for h in self.api.get(f"/workflows/{self.id}/config/history") if h["version"] > (self.state.get("version") or 0)]
            for h in sorted(hist, key=lambda h: h["version"]):
                latest = h["version"] == new_v
                self.s.x("INSERT OR REPLACE INTO config_hist VALUES(?,?,?,?,?,?,?,?)",
                         (self.id, h["version"], h.get("applied_at") or self.ctl.now, h["actor"], json.dumps(h.get("changed_dims")),
                          h.get("proposal_id"), h.get("approval_id"), json.dumps(self.cfg) if latest else None))
                if h["actor"] == "supervisor":
                    self.on_supervisor_edit(h)
                else:
                    if set(h.get("changed_dims") or []) & {"welcome_message", "voice", "cohorts"}:
                        self.state["last_cf_apply_minute"] = self.ctl.minute
                    self.audit("config_changed", h["actor"], f"v{h['version']} by {h['actor']}: {h.get('changed_dims')}",
                               {"history": h}, h.get("proposal_id"))
                    if "prompt_version" in (h.get("changed_dims") or []):
                        self.state["regime_tb"] = self.now_tb
                        self.state["prompt_live_hb"] = self.now_hb
            self.state["version"] = new_v
            self.save()

    def on_supervisor_edit(self, h):
        dims = h.get("changed_dims") or []
        d, _, _ = self.tparts
        for dim in dims:
            if dim in ("welcome_message", "voice", "schedule", "cohorts", "caller_id"):
                self.state["hold"][dim] = d + HOLD_DAYS
        if "cohorts" in dims:
            self.state["hold"]["welcome_message"] = self.state["hold"]["voice"] = d + HOLD_DAYS
        for dim in ("welcome_message", "voice"):
            if dim in dims:
                self.state.setdefault("sup_set", {})[dim] = dist_of(self.cfg, "default", dim)
        for dim in ("schedule", "caller_id"):     # no "win" concept for these: protected until the supervisor changes them again
            if dim in dims:
                self.state.setdefault("sup_set", {})[dim] = True
        if "prompt_version" in dims:
            self.state["regime_tb"] = self.now_tb
            self.state["prompt_live_hb"] = self.now_hb
        self.audit("supervisor_edit", "supervisor", f"supervisor changed {dims} (v{h['version']}); not overwritten - dims held "
                   f"{HOLD_DAYS}d, in-flight proposals on the old base will be re-proposed", {"history": h, "hold": self.state["hold"]})
        # any proposal built on the old base is stale; gov.reconcile detects it at apply time (409/base mismatch)

    def hold_dims(self):
        d, _, _ = self.tparts
        for k in [k for k, v in self.state["hold"].items() if v <= d]:
            del self.state["hold"][k]
        return set(self.state["hold"])

    # ------------------------------------------------------------------ tick
    def tick(self):
        self.sync_config()
        self.gov.recover_auto_intents(self.ctl.now, self.id, self.version)
        events = self.gov.reconcile(self.ctl.now, self.id, self.version)
        if events:
            self.sync_config()
            for pid, kind, st in events:
                if st in ("rejected", "expired", "lapsed", "stale"):
                    # product rule: expiry == rejection; re-queue later with fresh data, never replay the stale payload
                    if st != "stale":
                        self.state["backoff_until"] = self.ctl.minute + BACKOFF_H * 60
                        self.state["rejected_streak"] = self.state.get("rejected_streak", 0) + 1
                    self.state["needs_reopt"] = True
                elif st == "applied":
                    self.state["rejected_streak"] = 0
                    if kind == "opt":
                        self.state["last_opt_applied_minute"] = self.ctl.minute
            self.save()
        self.continue_auto_steps()
        self.watch_halluc()
        self.watch_dids()
        self.watch_decay()
        if self.ctl.minute % 60 == 0:
            self.optimize()
            self.watch_drift()
        self.save()

    # ================================================================== hallucination incidents (C8)
    def watch_halluc(self):
        inc = self.state.get("incident_h")
        prompt = self.cfg.get("prompt_version")
        since = self.state.get("prompt_live_hb", -10 ** 6)
        recent_change = since > self.now_hb - 24      # a known prompt change is a strong prior: lower bar, same test
        st = detect.hallucination_status(self.s, self.id, prompt, self.now_hb, since, changed=recent_change)
        if inc is None:
            if st["spike"]:
                self.open_halluc(st)
            else:
                if (st["n"] >= 300 and st["rate"] <= 1.5 * st["baseline"] and prompt != self.state.get("prompt_good")
                        and self.now_hb - since >= 6):
                    self.state["prompt_good"] = prompt
                    self.audit("prompt_good", prompt, f"{prompt} observed clean over {st['n']} connected calls", st)
            return
        step = inc["step"]
        if step in ("proposed", "applying"):
            ap = [a for a in self.gov.active(self.id) if a[0] == inc.get("proposal_id")]
            row = self.s.q("SELECT status FROM proposals WHERE proposal_id=?", (inc.get("proposal_id"),))
            status = row[0][0] if row else None
            if status == "applied":
                inc["step"] = "verifying"; inc["applied_minute"] = self.ctl.minute
                self.state["prompt_live_hb"] = self.now_hb
                self.audit("incident_fix_applied", prompt, f"fix applied; verifying {prompt} on live traffic", inc, inc.get("proposal_id"))
            elif status in ("rejected", "expired", "lapsed", "stale", "failed", "refused", None):
                self.audit("incident_fix_failed", prompt, f"fix proposal ended as {status}; re-opening incident", inc)
                self.close_inc(inc, "reopened")
                self.state["incident_h"] = None
        elif step == "verifying":
            vs = detect.hallucination_status(self.s, self.id, prompt, self.now_hb, self.state.get("prompt_live_hb", self.now_hb))
            # Verification has the opposite burden of proof from detection: "not provably a spike" is NOT "fixed".
            # Still elevated = point estimate above 1.5x baseline AND p<0.05 against baseline; decide only with enough calls.
            elevated = vs["rate"] > 1.5 * vs["baseline"] and vs["p_value"] < 0.05
            if vs["n"] >= 100 and not elevated:
                ttf = (self.ctl.minute - inc["detected_minute"])
                self.audit("incident_resolved", prompt, f"hallucination back to baseline ({vs['rate']:.3%} vs baseline "
                           f"{vs['baseline']:.3%}, p={vs['p_value']:.2f}) over {vs['n']} calls; {ttf} sim-min from detection to verified fix", vs)
                self.close_inc(inc, "resolved")
                self.state["prompt_good"] = prompt
                self.state["incident_h"] = None
            elif vs["n"] >= 300 and elevated:
                self.audit("incident_fix_ineffective", prompt, f"hallucination still elevated under {prompt}: {vs}", vs)
                self.close_inc(inc, "failed")
                self.state["incident_h"] = None

    def close_inc(self, inc, status):
        self.s.x("UPDATE incidents SET status=?, resolved_ts=? WHERE id=?", (status, self.ctl.now, inc["db_id"]))

    def open_halluc(self, st):
        prompt = self.cfg["prompt_version"]
        cur = self.s.x("INSERT INTO incidents(wf,kind,subject,status,onset_ts,detected_ts,detail) VALUES(?,?,?,?,?,?,?)",
                       (self.id, "hallucination", prompt, "open", self.ctl.now, self.ctl.now, json.dumps(st)))
        inc = {"db_id": cur.lastrowid, "step": "detected", "prompt": prompt, "detected_minute": self.ctl.minute, "evidence": st}
        self.state["incident_h"] = inc
        self.audit("incident_opened", prompt, f"hallucination spike on {prompt}: {st['flags']}/{st['n']} flagged calls "
                   f"({st['rate']:.2%} vs baseline {st['baseline']:.2%}, p={st['pv'] if 'pv' in st else st['p_value']:.1e})", st)
        self.save()
        good = self.state.get("prompt_good")
        thr = self.gv.get("min_validation_pass_rate", 0.97)
        cands = []
        if good and good != prompt and good in self.info["options"]["prompt_version"] or (good and good != prompt):
            cands.append((good, "last known-good prompt (clean on live traffic)"))
        chosen = None
        for p, why in cands:
            r = self.ctl.validate(self.id, p, 300, "incident: validate rollback target")
            if r and r["pass_rate"] >= thr:
                chosen = (p, r, why); break
        tried = []
        if not chosen:
            sug = self.ctl.suggest(self.id, f"hallucination spike on prompt {prompt} ({st['rate']:.1%} flagged calls)")
            for s_ in (sug or {}).get("suggestions", []):
                p = s_["prompt_version"]
                if p == prompt:
                    continue
                r = self.ctl.validate(self.id, p, 300, "incident: validate LLM suggestion")
                tried.append((p, r and r["pass_rate"], s_["summary"]))
                if r and r["pass_rate"] >= thr:
                    # prefer fixes that don't look like "read the compliance script verbatim" (kills engagement)
                    bad = any(w in s_["summary"].lower() for w in ("verbatim", "strict"))
                    score = (not bad, r["pass_rate"])
                    if not chosen or score > chosen[3]:
                        chosen = (p, r, "LLM-suggested: " + s_["summary"], score)
        if not chosen:
            self.audit("incident_no_fix", prompt, "no candidate passed validation; escalate to human", {"tried": tried})
            inc["step"] = "escalated"
            return
        p, r = chosen[0], chosen[1]
        cfg = copy.deepcopy(self.cfg)
        cfg["prompt_version"] = p
        body = {
            "change_summary": f"Safety fix: switch prompt {prompt} -> {p} after hallucination spike ({st['rate']:.1%} of calls flagged)",
            "diff": {"prompt_version": {"from": prompt, "to": p}},
            "affected_leads": self.leads_per_day() ,
            "dry_run": {"method": "validation run on synthetic conversations + live incident stats",
                        "validation": {k: r[k] for k in ("validation_run_id", "n", "pass_rate", "failures")},
                        "live_hallucination_rate": st["rate"], "baseline": st["baseline"], "n_live_calls": st["n"]},
            "impact_score": round(min(1.0, 0.5 + min(st["rate"] / max(st["baseline"], 1e-3), 10) / 20), 3),
            "rationale": f"{st['flags']} of {st['n']} connected calls flagged for hallucination under {prompt} vs a baseline of "
                         f"{st['baseline']:.2%} (binomial p={st['p_value']:.1e}). {chosen[2]}. Validation {r['validation_run_id']}: "
                         f"pass_rate {r['pass_rate']:.3f} on n={r['n']} (threshold {thr}). Engagement is checked after apply.",
            "evidence": {"validation_run_id": r["validation_run_id"]},
        }
        if not self.approver_window_ok(urgent=True):
            inc["step"] = "wait_window"; inc["pending_body"] = body; inc["pending_cfg"] = cfg
            self.save(); return
        pid = self.gov.submit(self.ctl.now, self.id, "incident_prompt", self.version, cfg, body)
        inc["step"] = "proposed" if pid else "detected"
        inc["proposal_id"] = pid
        self.save()

    def retry_waiting_incident(self):
        inc = self.state.get("incident_h")
        if inc and inc.get("step") == "wait_window" and self.approver_window_ok(urgent=True):
            pid = self.gov.submit(self.ctl.now, self.id, "incident_prompt", self.version, inc["pending_cfg"], inc["pending_body"])
            inc["step"] = "proposed" if pid else "wait_window"
            inc["proposal_id"] = pid

    # ================================================================== caller-ID health (C5)
    def did_dist(self):
        return dist_of(self.cfg, "default", "caller_id")

    def watch_dids(self):
        self.retry_waiting_incident()
        dids = self.info["options"]["caller_id"]
        flagged = self.state["did_flagged"]
        stt = detect.did_status(self.s, self.id, self.now_hb, dids)
        new = [d for d, r in stt.items() if r["flagged"] and d not in flagged]
        for d in new:
            flagged[d] = {"ts": self.ctl.now, "minute": self.ctl.minute, **stt[d]}
            self.s.x("INSERT INTO incidents(wf,kind,subject,status,onset_ts,detected_ts,detail) VALUES(?,?,?,?,?,?,?)",
                     (self.id, "caller_id", d, "open", self.ctl.now, self.ctl.now, json.dumps(stt[d])))
            self.audit("incident_opened", d, f"caller ID {d} degraded: pickup {stt[d]['pickup']:.1%} vs own history "
                       f"{stt[d]['baseline_pickup']} and peers {stt[d]['peer_pickup']} (z_base={stt[d]['z_base']}, z_peer={stt[d]['z_peer']}, "
                       f"n={stt[d]['dials']})", stt[d])
        # recovery probe: a flagged DID kept at the probe floor is re-tested against peers
        for d in list(flagged):
            if d in new:
                continue
            r = stt.get(d)
            if r and not r["flagged"] and r["dials"] >= 150 and r["peer_pickup"] and r["pickup"] >= 0.85 * r["peer_pickup"]:
                del flagged[d]
                self.audit("did_recovered", d, f"caller ID {d} probe traffic back near peers ({r['pickup']:.1%} vs {r['peer_pickup']:.1%})", r)
        if new or flagged:
            self.apply_did_target(urgent=bool(new))
        self.save()

    def did_target(self):
        """Target default caller_id distribution: flagged -> probe floor, unseen -> small exploration share, rest ~ pickup^4."""
        dids = self.info["options"]["caller_id"]
        flagged = self.state["did_flagged"]
        cur = self.did_dist()
        rows = {r[0]: (r[1], r[2]) for r in self.s.q(
            "SELECT did,SUM(dials),SUM(conn) FROM agg_did WHERE wf=? AND hb>? GROUP BY did", (self.id, self.now_hb - 48))}
        floor, expl = 0.02, 0.2       # unseen IDs get a real share: spreading per-ID load beat a cautious 8% probe on all 5 test worlds
        w = {}
        healthy = [d for d in dids if d not in flagged]
        if not healthy:
            return cur
        seen = [d for d in healthy if rows.get(d, (0, 0))[0] >= 100]
        unseen = [d for d in healthy if d not in seen]
        exp_total = min(0.5, expl * len(unseen)) if seen else 0.0
        remaining = 1 - floor * len([d for d in dids if d in flagged]) - exp_total
        for d in unseen:
            w[d] = expl if seen else 1.0
        if seen:
            sc = {d: (rows[d][1] / rows[d][0]) for d in seen}      # ~uniform over healthy IDs: spreads per-ID load, no winner-take-all
            t = sum(sc.values())
            for d in seen:
                w[d] = remaining * sc[d] / t
        for d in dids:
            if d in flagged:
                w[d] = floor
        return norm(w)

    def apply_did_target(self, urgent=False):
        if "caller_id" in self.hold_dims():
            return
        if "caller_id" in self.state.get("sup_set", {}) and not self.state["did_flagged"]:
            return        # supervisor-chosen caller-ID split: only a health incident may move it
        tgt = self.did_target()
        cur = self.did_dist()
        if tv(cur, tgt) < (0.04 if urgent else 0.15):
            return
        if not urgent:
            d, _, _ = self.tparts
            if self.state.get("did_opt_day") == d:
                return
            self.state["did_opt_day"] = d
        cfg = copy.deepcopy(self.cfg)
        cfg["allocations"]["default"]["caller_id"] = tgt
        aa = self.gv["auto_apply"]
        if aa["enabled"] and "caller_id" in aa["allowed_dims"]:
            self.state["auto_target"] = {"cfg_default_caller_id": tgt, "why": "caller_id health/exploration"}
            self.continue_auto_steps()
        else:
            self.propose_ops_only(cfg, "caller_id", "Caller-ID rotation", f"caller_id {cur} -> {tgt}", urgent)

    def continue_auto_steps(self):
        """Step the live caller_id distribution toward the target in increments <= policy max_shift (one PUT per tick)."""
        tgt = (self.state.get("auto_target") or {}).get("cfg_default_caller_id")
        if not tgt:
            return
        cur = self.did_dist()
        d = tv(cur, tgt)
        if d < 0.01:
            self.state["auto_target"] = None
            return
        ms = max(self.gv["auto_apply"]["max_shift"] * 0.9, 0.01)
        step = tgt if d <= ms else {k: cur.get(k, 0) + (tgt.get(k, 0) - cur.get(k, 0)) * (ms / d) for k in set(cur) | set(tgt)}
        step = norm(step)
        cfg = copy.deepcopy(self.cfg)
        cfg["allocations"]["default"]["caller_id"] = step
        flagged = list(self.state["did_flagged"])
        ok, res = self.gov.auto_apply(
            self.ctl.now, self.id, "caller_id_rotation", self.version, cfg,
            rationale=f"caller-ID health: flagged={flagged}; step toward {tgt} (TV step {min(d, ms):.2f} <= policy max_shift {self.gv['auto_apply']['max_shift']})",
            summary=f"caller_id {cur} -> {step} (target {tgt})", diff={"caller_id": {"from": cur, "to": step, "target": tgt}})
        if ok:
            self.cfg = cfg
            self.sync_config()
        else:
            self.state["auto_target"] = None
            self.state["auto_refused"] = self.ctl.now
            self.audit("auto_apply_fallback", "caller_id", f"auto-apply refused ({res}); falling back to approval path")
            self.propose_ops_only(cfg, "caller_id", "Caller-ID rotation", f"caller_id -> {tgt}", True)

    def propose_ops_only(self, cfg, dim, title, detail, urgent):
        if self.gov.active(self.id, {"ops", "opt"}) or not self.approver_window_ok(urgent):
            return
        if self.gov.submitted_since(self.id, self.ctl.hours_ago(24)) >= self.gv["max_requests_per_24h"]:
            return
        p = self.planner
        body = {"change_summary": f"{title}: {detail}",
                "diff": {dim: {"from": dist_of(self.cfg, 'default', 'caller_id'), "to": dist_of(cfg, 'default', 'caller_id')}},
                "affected_leads": self.leads_per_day(),
                "dry_run": {"method": "population stats on recent dials per caller ID",
                            "caller_id_status": detect.did_status(self.s, self.id, self.now_hb, self.info["options"]["caller_id"]),
                            "flagged": self.state["did_flagged"]},
                "impact_score": 0.6 if urgent else 0.3,
                "rationale": "Operational change (caller-ID routing). Flagged IDs lose traffic; others share it. No script/voice change."}
        pid = self.gov.submit(self.ctl.now, self.id, "ops", self.version, cfg, body)
        if pid:
            self.save()

    # ================================================================== decay detection & rollback (C7)
    def watch_decay(self):
        if self.ctl.minute % 60:
            return
        info = self.info
        prim, (num, den), gname, _ = kpi(info)
        idx = {"dials": 0, "conn": 1, "eng": 2}
        cohorts = [Cohort.from_cfg(c) for c in self.cfg.get("cohorts", [])]
        lo_tb = self.now_tb - 6
        for dim, col in (("welcome_message", "w"), ("voice", "v")):
            if dim in self.hold_dims():
                continue
            ref = self.state["ref"][dim]
            rows = self.s.q(f"SELECT cell,{col},SUM(dials),SUM(conn),SUM(eng) FROM agg_var WHERE wf=? AND tb>? GROUP BY cell,{col}",
                            (self.id, lo_tb))
            acc = defaultdict(lambda: defaultdict(lambda: [0, 0]))
            for cell, v, d, c, e in rows:
                cid = assign(cohorts, cell)
                a = acc[cid][v]
                a[0] += (d, c, e)[idx[num]]; a[1] += (d, c, e)[idx[den]]
            for cid, vv in acc.items():
                dist = dist_of(self.cfg, cid, dim)
                if not dist:
                    continue
                win = max(dist, key=dist.get)
                if win == ref or dist[win] < 0.5 or win in self.state["bans"].get(dim, {}):
                    continue
                kw, nw = vv.get(win, (0, 0)); kr, nr = vv.get(ref, (0, 0))
                if nw < 150 or nr < 80:
                    continue
                from .stats import log_ratio
                y, var = log_ratio(kw, nw, kr, nr)
                se = math.sqrt(var)
                decayed = (y + 1.28 * se < math.log(1.015)) or (y + 2.0 * se < 0)
                if decayed:
                    self.state["bans"].setdefault(dim, {})[win] = {"ts": self.ctl.now, "cohort": cid, "lift_recent": round(math.exp(y) - 1, 4),
                                                                   "se": round(se, 4), "n_win": nw, "n_ref": nr}
                    self.audit("winner_decayed", f"{dim}={win}@{cid}",
                               f"{win} ({dim}, cohort {cid}) no longer beats reference {ref}: recent lift {math.exp(y) - 1:+.1%} "
                               f"(se {se:.3f}, n={nw}/{nr}); banned and rolling back", self.state["bans"][dim][win])
                    self.state["rollback_pending"] = True
                    self.save()
                    self.optimize(urgent=True)

    # ================================================================== drift alerts
    def watch_drift(self):
        if self.ctl.minute % (60 * 6):
            return
        dr = detect.kpi_drift(self.s, self.id, self.info, self.now_hb)
        for name, v in dr.items():
            if v and v["drift"]:
                key = f"drift:{name}"
                last = self.state.get(key, -999)
                if self.ctl.minute - last > 24 * 60:
                    self.state[key] = self.ctl.minute
                    self.audit("drift_detected", name, f"{name} fell to {v['recent']:.1%} from {v['baseline']:.1%} ({v['rel']:+.1%}, z={v['z']}, n={v['n']})", v)
                    self.state["needs_reopt"] = True

    # ================================================================== optimiser: build governed proposals
    def leads_per_day(self):
        d, _, _ = self.tparts
        r = self.s.q("SELECT day,SUM(n) FROM lead_day WHERE wf=? AND day<? GROUP BY day ORDER BY day DESC LIMIT 3", (self.id, d + 1))
        vals = [x[1] for x in r if x[1]]
        return int(sum(vals) / len(vals)) if vals else 0

    def optimize(self, urgent=False):
        if self.state.get("incident_h") and self.state["incident_h"]["step"] not in ("escalated",):
            return
        if self.gov.active(self.id, {"opt", "ops"}):
            return
        d, h, _ = self.tparts
        if not urgent:
            if self.state.get("backoff_until") and self.ctl.minute < self.state["backoff_until"]:
                return
            if not self.approver_window_ok():
                # nothing to do in the window => no daily evaluation; mark so we evaluate once window opens
                return
            if self.state["last_eval_day"] == d and not self.state.get("needs_reopt"):
                return
            if self.ctl.minute - self.state.get("last_opt_applied_minute", -10 ** 9) < 36 * 60:
                return      # cooldown: let the last change produce evidence before proposing the next one
            if self.info.get("mid_flight") == "next_campaign_only" and \
                    self.ctl.minute - self.state.get("last_cf_apply_minute", -10 ** 9) < 24 * 60:
                return      # agent-facing changes only reach the *next* campaign; wait for evidence of the last one
        else:
            if not self.approver_window_ok(urgent=True) and not self.can_auto_all():
                return
        cap = min(2, self.gv["max_requests_per_24h"] - 1)       # one slot is kept for incidents; supervisors asked for <=2/day
        if not urgent and self.gov.submitted_since(self.id, self.ctl.hours_ago(24)) >= cap:
            return
        self.state["last_eval_day"] = d
        self.state["needs_reopt"] = False
        hold = self.hold_dims()
        plan = self.planner.plan(self.id, self.info, self.state, self.now_tb, self.cfg)
        desired = self.planner.synthesize(self.cfg, plan, self.info, self.state, hold | ({"schedule"} if "schedule" in self.state.get("sup_set", {}) else set()))
        # caller-id plan (part of the same desired state)
        if "caller_id" not in hold and ("caller_id" not in self.state.get("sup_set", {}) or self.state["did_flagged"]):
            tgt = self.did_target()
            if tv(self.did_dist(), tgt) >= 0.15:
                desired["allocations"]["default"]["caller_id"] = tgt
        desired = self.settle(desired, plan)
        dims = changed_dims(self.cfg, desired)
        ev = {"features": plan["feats"], "importance": {k: round(v, 2) for k, v in plan["importance"].items()},
              "hour_importance": {k: round(v, 2) for k, v in plan["hour_importance"].items()}, "analysis": plan["analysis"],
              "blocked": plan["blocked"], "window_tbs": plan["window_tbs"], "hold": sorted(hold), "bans": self.state["bans"]}
        if not dims:
            self.audit("evaluation", "no_change", "evaluated cohorts/variants/call-time; no change clears the evidence bar", ev)
            self.save()
            return
        # path selection: customer-facing => approval; operational-only and permitted => auto-apply
        aa = self.gv["auto_apply"]
        auto_ok = aa["enabled"] and dims <= set(aa["allowed_dims"]) and not (dims & CUSTOMER_FACING)
        rollback_auto = (urgent and aa["enabled"] and dims <= set(aa["allowed_dims"]) and "cohorts" not in dims)
        if auto_ok or rollback_auto:
            self.auto_path(desired, dims, plan, ev, rollback=rollback_auto and bool(dims & CUSTOMER_FACING))
        else:
            self.approval_path(desired, dims, plan, ev, urgent)
        self.save()

    def can_auto_all(self):
        aa = self.gv["auto_apply"]
        return aa["enabled"] and {"welcome_message", "voice"} <= set(aa["allowed_dims"])

    def settle(self, desired, plan):
        """Suppress immaterial changes (churn): keep the live value of any dim whose change is below the materiality bar."""
        live = self.cfg
        # allocations (welcome/voice): material if cohort set changed or any distribution moved TV>0.1
        cohorts_changed = desired.get("cohorts") != live.get("cohorts")
        mat = cohorts_changed
        has_win = any(p[d][0] == "win" for p in [plan["default_plan"], *plan["cohort_plans"].values()] for d in DIMS)
        thr = 0.1 if has_win else 0.25     # exploration-only refinements are not worth an approver's attention
        for cid in set(desired["allocations"]) | set(live.get("allocations", {})):
            for dim in DIMS:
                if tv(dist_of(live, cid, dim) or {"x": 1}, dist_of(desired, cid, dim) or {"x": 1}) > thr:
                    mat = True
        if not mat:
            desired["cohorts"] = live.get("cohorts", [])
            for cid in list(desired["allocations"]):
                for dim in DIMS:
                    lv = live.get("allocations", {}).get(cid, {}).get(dim)
                    if lv is not None:
                        desired["allocations"].setdefault(cid, {})[dim] = lv
                    else:
                        desired["allocations"].get(cid, {}).pop(dim, None)
            for cid in [c for c, v in desired["allocations"].items() if not v and c != "default"]:
                del desired["allocations"][cid]
        # schedule: material if mean |dw| >= 0.15 on any cohort table or table set changed
        lh = (live.get("schedule") or {}).get("hour_weights", {})
        dh = (desired.get("schedule") or {}).get("hour_weights", {})
        diff = 0.0
        if set(lh) != set(dh):
            diff = 1.0
        else:
            for k in dh:
                diff = max(diff, sum(abs(dh[k].get(h, 0) - lh[k].get(h, 0)) for h in dh[k]) / max(len(dh[k]), 1))
        if diff < 0.15:
            desired["schedule"] = copy.deepcopy(live.get("schedule", {"hour_weights": {}, "lead_preferred_hour": {}}))
        return desired

    # ------------------------------------------------------------------ evidence for proposals
    def evidence(self, desired, plan):
        rows = self.planner.window_rows(self.id, plan["window_tbs"][0])
        cell_vol = defaultdict(float)
        for r in rows:
            cell_vol[r[0]] += r[4]
        old, vo = self.planner.expected_rel(self.cfg, plan, self.info, self.state, cell_vol) if cell_vol else (1.0, 0.0)
        new, vn = self.planner.expected_rel(desired, plan, self.info, self.state, cell_vol) if cell_vol else (1.0, 0.0)
        gain = new / old - 1 if old else 0.0
        se = math.sqrt(vo + vn) / max(old, 1e-9)
        lcb = gain - 1.64 * se
        # call-time: model-based replay of the hour tables on observed pickup per (cohort, hour)
        hgain = self.hour_gain(desired)
        return {"model_gain": round(gain, 4), "model_gain_lcb": round(lcb, 4), "model_se": round(se, 4),
                "schedule_pickup_gain": hgain, "n_dials_window": int(sum(cell_vol.values())),
                "window_days": round((plan["window_tbs"][1] - plan["window_tbs"][0]) / 4, 1)}

    def hour_gain(self, desired):
        lh = (self.cfg.get("schedule") or {}).get("hour_weights", {})
        dh = (desired.get("schedule") or {}).get("hour_weights", {})
        if lh == dh or not dh:
            return 0.0
        d, _, _ = self.tparts
        rows = self.planner.hour_tables(self.id, d - 21)
        ch_new = [Cohort.from_cfg(c) for c in desired.get("cohorts", [])]
        pools, rate = defaultdict(float), {}
        agg = defaultdict(lambda: [0, 0])
        for h, cell, dd, c, e in rows:
            cid = assign(ch_new, cell)
            a = agg[(cid, h)]
            a[0] += dd; a[1] += c
            pools[cid] += dd
        hours = sorted({k[1] for k in agg})

        def tbl(tables, cid, h):
            t = tables.get(cid) or tables.get("default")
            return (t or {}).get(str(h), 1.0) if t else 1.0

        def expected(tables):
            tot = 0.0
            for h in hours:
                num = den = 0.0
                for cid, pool in pools.items():
                    dd, cc = agg.get((cid, h), (0, 0))
                    if dd < 20:
                        continue
                    w = pool * tbl(tables, cid, h)
                    num += w * cc / dd; den += w
                tot += num / den if den else 0
            return tot / len(hours)
        e0, e1 = expected(lh), expected(dh)
        return round(e1 / e0 - 1, 4) if e0 else 0.0

    def affected(self, desired):
        d, _, _ = self.tparts
        rows = self.s.q("SELECT cell,SUM(n) FROM lead_day WHERE wf=? AND day>=? AND day<=? GROUP BY cell", (self.id, d - 3, d))
        days = max(1, len({r[0] for r in self.s.q("SELECT DISTINCT day FROM lead_day WHERE wf=? AND day>=? AND day<=?", (self.id, d - 3, d))}))
        co, cn = [Cohort.from_cfg(c) for c in self.cfg.get("cohorts", [])], [Cohort.from_cfg(c) for c in desired.get("cohorts", [])]
        n = 0
        for cell, k in rows:
            a, b = assign(co, cell), assign(cn, cell)
            changed = any(tv(dist_of(self.cfg, a, dm) or {"x": 1}, dist_of(desired, b, dm) or {"x": 1}) > 0.05
                          for dm in ("welcome_message", "voice", "caller_id"))
            sw = (self.cfg.get("schedule") or {}).get("hour_weights", {}).get(a) != (desired.get("schedule") or {}).get("hour_weights", {}).get(b)
            if changed or sw:
                n += k
        return int(n / days)

    def diff(self, desired):
        out = {}
        oc, nc = {c["id"] for c in self.cfg.get("cohorts", [])}, {c["id"] for c in desired.get("cohorts", [])}
        if oc != nc:
            out["cohorts"] = {"added": sorted(nc - oc), "removed": sorted(oc - nc),
                              "definitions": {c["id"]: c["where"] for c in desired.get("cohorts", [])}}
        al = {}
        for cid in set(desired["allocations"]) | set(self.cfg.get("allocations", {})):
            for dim in ("welcome_message", "voice", "caller_id"):
                a, b = dist_of(self.cfg, cid, dim), dist_of(desired, cid, dim)
                if cid in desired["allocations"] and a != b:
                    al.setdefault(cid, {})[dim] = {"from": a, "to": b}
        if al:
            out["allocations"] = al
        lh = (self.cfg.get("schedule") or {}).get("hour_weights", {})
        dh = (desired.get("schedule") or {}).get("hour_weights", {})
        if lh != dh:
            out["schedule.hour_weights"] = {"tables_changed": sorted(k for k in dh if dh.get(k) != lh.get(k)), "tables": dh}
        return out

    def describe(self, desired, plan, dims, ev):
        parts = []
        for cid in ["default"] + [c.id for c in plan["cohorts"]]:
            pl = plan["default_plan"] if cid == "default" else plan["cohort_plans"].get(cid)
            if not pl:
                continue
            for dim in DIMS:
                k, v, t, se, avoid = pl[dim]
                if k == "win":
                    parts.append(f"{dim} {v} for {cid} (lower-bound est. {math.exp(max(t - 1.64 * se, 0)) - 1:+.0%})")
        if any(pl[dim][0] == "explore" for pl in [plan["default_plan"]] for dim in DIMS):
            parts.append("keep testing challengers on a bounded share")
        if "schedule" in dims:
            parts.append(f"re-weight call hours per cohort (est. pickup {ev['schedule_pickup_gain']:+.1%})")
        if "caller_id" in dims:
            parts.append("rebalance caller IDs")
        return "; ".join(parts) or f"update {sorted(dims)}"

    # ------------------------------------------------------------------ paths
    def approval_path(self, desired, dims, plan, ev, urgent):
        if not self.approver_window_ok(urgent):
            return
        e = self.evidence(desired, plan)
        explore = any(plan["default_plan"][d][0] == "explore" for d in DIMS) or any(
            p[d][0] == "explore" for p in plan["cohort_plans"].values() for d in DIMS)
        impact = max(0.0, e["model_gain_lcb"]) / 0.08 + max(0.0, e["schedule_pickup_gain"]) / 0.05
        if explore and dims & {"welcome_message", "voice"}:
            impact += 0.1       # option value of bounded exploration; no promised lift
        impact = round(min(1.0, impact), 3)
        rationale = (f"Evidence ({e['n_dials_window']} dials over {e['window_days']}d, cohort partition on {plan['feats'] or 'no feature'}): "
                     f"model-estimated primary-KPI gain {e['model_gain']:+.1%} (95% lower bound {e['model_gain_lcb']:+.1%}); "
                     f"call-time pickup gain {e['schedule_pickup_gain']:+.1%}. Winners need z>={2.5} and lift>=2% in their cohort, "
                     f"challengers kept at bounded shares, a reference holdout stays live for decay detection. "
                     f"Guardrail ({list(self.info['objective']['guardrail'])[0]}) screened; blocked variants: {plan['blocked'] or 'none'}.")
        body = {"change_summary": f"{self.id}: " + self.describe(desired, plan, dims, e),
                "diff": self.diff(desired), "affected_leads": self.affected(desired),
                "dry_run": {"method": "model-based counterfactual replay over observed per-cell arm rates (not a live test)",
                            "estimate": e, "analysis": plan["analysis"]},
                "impact_score": impact, "rationale": rationale}
        pid = self.gov.submit(self.ctl.now, self.id, "opt", self.version, desired, body)
        self.audit("optimizer_proposal", "approval", body["change_summary"], {**ev, "estimate": e}, pid)

    def auto_path(self, desired, dims, plan, ev, rollback=False):
        """Operational (schedule / caller_id) changes inside the signed policy, or a protective rollback of a decayed winner."""
        e = self.evidence(desired, plan)
        aa = self.gv["auto_apply"]
        # allocation moves are limited by max_shift per call: step the allocations, apply schedule at once
        cfg = copy.deepcopy(self.cfg)
        done = True
        for cid in set(desired["allocations"]) | set(cfg["allocations"]):
            for dim in ("welcome_message", "voice", "caller_id"):
                tgt, cur = dist_of(desired, cid, dim), dist_of(cfg, cid, dim)
                if cid not in desired["allocations"] or not tgt or tgt == cur:
                    continue
                dtv = tv(cur or tgt, tgt)
                ms = max(aa["max_shift"] * 0.9, 0.01)
                if dtv <= ms:
                    cfg["allocations"].setdefault(cid, {})[dim] = tgt
                else:
                    done = False
                    cfg["allocations"].setdefault(cid, {})[dim] = norm({k: cur.get(k, 0) + (tgt.get(k, 0) - cur.get(k, 0)) * ms / dtv
                                                                      for k in set(cur) | set(tgt)})
        if "schedule" in dims:
            cfg["schedule"] = desired["schedule"]
        if changed_dims(self.cfg, cfg) <= set() or changed_dims(self.cfg, cfg) - set(aa["allowed_dims"]):
            return
        kind = "rollback" if rollback else "ops_auto"
        ok, res = self.gov.auto_apply(
            self.ctl.now, self.id, kind, self.version, cfg,
            rationale=("Protective rollback of a decayed winner; " if rollback else "Operational change within signed policy; ") +
                      f"model gain {e['model_gain']:+.1%}, call-time pickup gain {e['schedule_pickup_gain']:+.1%}. "
                      f"{'Stepped to respect max_shift.' if not done else ''}",
            summary=self.describe(desired, plan, dims, e), evidence={"estimate": e}, diff=self.diff(cfg))
        if ok:
            self.cfg = cfg
            self.state["needs_reopt"] = not done      # keep stepping next hour
            self.sync_config()
        else:
            self.approval_path(desired, dims, plan, ev, urgent=rollback)
