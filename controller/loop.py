"""The always-on loop: advance the world, ingest, and run every workflow's control step. All durable state is in
SQLite, so the process can be killed at any instruction and simply restarted."""
import datetime as dt
import json
import os
import sys
import threading
import time

from .api import Api, ApiError
from .gov import Gov
from .ingest import Ingestor
from .store import Store
from .wfctl import WF

STEP_MIN = int(os.environ.get("CTL_STEP_MIN", "15"))


class Controller:
    def __init__(self, url, db_path, view_port=None):
        self.log = lambda *a: print(time.strftime("%H:%M:%S"), *a, file=sys.stderr, flush=True)
        self.api = Api(url, self.log)
        self.s = Store(db_path)
        self.api.wait_ready()
        self.check_world()
        self.gov = Gov(self.s, self.api, self.log)
        self.ing = Ingestor(self.s, self.api, self.log)
        self.now, self.minute, self.credits = None, 0, None
        self.credit_total = None
        self.wfs = {}
        self.stats = {"ingest_eps": 0.0, "decision_lag_s": 0.0, "events": 0, "tick_s": 0.0}
        self.view_port = view_port

    def check_world(self):
        """A state DB belongs to exactly one simulated world. If the simulator is a different scenario, or a fresh world
        of the same scenario (its clock is behind what we already processed), the old cursors/state are meaningless and
        would silently skip events: wipe and start clean."""
        st = self.api.get("/sim/state")
        fp = {"scenario": st["scenario"], "end_minute": st["end_minute"]}
        old, last = self.s.kget("world"), self.s.kget("last_minute", 0)
        if old is not None and (old != fp or st["sim_minute"] < last):
            self.log(f"[boot] state DB belongs to another world ({old}, minute {last}) - resetting")
            for (t,) in self.s.q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                self.s.x(f"DELETE FROM {t}")
        self.s.kset("world", fp)

    # ------------------------------------------------------------------ helpers used by workflow controllers
    def hours_ago(self, h):
        t = dt.datetime.fromisoformat(self.now) - dt.timedelta(hours=h)
        return t.isoformat()

    def _credit_gate(self, wf, cost):
        """Fair share of credits across workflows, 25% held back for incidents of anyone. Incidents may dip into the reserve."""
        if self.credits is None:
            return True
        spent = self.s.q("SELECT COALESCE(SUM(cost),0) FROM credits WHERE wf=?", (wf,))[0][0]
        share = 0.75 * self.credit_total / max(len(self.wfs), 1)
        return self.credits - cost >= 0 and spent + cost <= max(share, 0.5 * self.credit_total) + 0.25 * self.credit_total

    def validate(self, wf, prompt, n, why):
        cost = -(-n // 100)
        if not self._credit_gate(wf, cost):
            self.log(f"[credits] refused {cost} for {wf}")
            return None
        try:
            r = self.api.post("/validation/runs", {"workflow_id": wf, "prompt_version": prompt, "n": n})
        except ApiError as e:
            self.log(f"[validate] {e}")
            return None
        self.credits = r.get("credits_remaining", self.credits)
        self.s.x("INSERT INTO credits VALUES(?,?,?,?,?)", (self.now, wf, f"validation {prompt} n={n}: {why}", cost, self.credits))
        self.s.decide(self.now, wf, "credit_spend", f"validation:{prompt}", f"{cost} credits: {why}; pass_rate={r['pass_rate']}", r)
        return r

    def suggest(self, wf, problem):
        if not self._credit_gate(wf, 3):
            return None
        try:
            r = self.api.post("/llm/suggest-fixes", {"workflow_id": wf, "problem": problem})
        except ApiError as e:
            self.log(f"[suggest] {e}")
            return None
        self.credits = r.get("credits_remaining", self.credits)
        self.s.x("INSERT INTO credits VALUES(?,?,?,?,?)", (self.now, wf, "llm suggest-fixes", 3, self.credits))
        self.s.decide(self.now, wf, "credit_spend", "suggest-fixes", f"3 credits: {problem}", r)
        return r

    # ------------------------------------------------------------------ main
    def refresh_state(self):
        st = self.api.get("/sim/state")
        self.now, self.minute, self.credits = st["ts"], st["sim_minute"], st["credits_remaining"]
        self.s.kset("last_minute", self.minute)
        if self.credit_total is None:
            self.credit_total = self.s.kget("credit_total") or self.credits
            self.s.kset("credit_total", self.credit_total)
        return st

    def run(self):
        self.api.wait_ready()
        if self.view_port:
            from .view import serve
            threading.Thread(target=serve, args=(self, self.view_port), daemon=True).start()
        st = self.refresh_state()
        # C3: bootstrap from history (idempotent through the cursor)
        _, n, secs, _ = self.ing.ingest_all("history")
        if n:
            self.log(f"[boot] history ingested: {n} events in {secs:.1f}s")
        for w in self.api.get("/workflows"):
            info = self.api.get(f"/workflows/{w['workflow_id']}")
            self.wfs[w["workflow_id"]] = WF(self, w["workflow_id"], info)
        self.ingest()
        for wf in self.wfs.values():
            wf.init_state()
        while True:
            t0 = time.time()
            st = self.refresh_state()
            self.control_step()
            if st["finished"]:
                break
            try:
                st = self.api.post("/sim/advance", {"minutes": STEP_MIN})
            except ApiError as e:
                if e.status == 409:
                    break
                raise
            self.ingest()
            self.refresh_state()
            self.stats["tick_s"] = time.time() - t0
            if st.get("finished"):
                self.control_step()
                break
        self.log("[done] scenario finished")
        self.s.decide(self.now, "-", "run_finished", "controller", "scenario finished", self.api.get("/sim/state"))

    def ingest(self):
        t0 = time.time()
        ctrl, n, secs, latest = self.ing.ingest_all("events")
        if n:
            self.stats["events"] += n
            self.stats["ingest_eps"] = n / max(secs, 1e-6)
        self.stats["decision_lag_s"] = time.time() - t0
        today = None
        if latest:
            from .ingest import day_of
            self.ing.prune(day_of(latest))
        self.s.x("INSERT INTO metrics VALUES(?,?,?)", (self.now, "ingest_eps", self.stats["ingest_eps"]))

    def control_step(self):
        for wf in self.wfs.values():
            try:
                wf.tick()
            except ApiError as e:
                self.log(f"[{wf.id}] api error {e}")
            except Exception as e:      # one bad workflow must not stop the platform loop
                import traceback
                self.log(f"[{wf.id}] ERROR {e!r}\n{traceback.format_exc()}")
                self.s.decide(self.now, wf.id, "controller_error", repr(e), traceback.format_exc()[-800:])
                try:
                    self.s.rollback()
                except Exception:
                    pass
        self.s.x("INSERT INTO metrics VALUES(?,?,?)", (self.now, "credits_remaining", self.credits or 0))
