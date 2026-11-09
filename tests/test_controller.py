"""Unit tests for the parts where a bug would be a client incident: statistics, cohorts, exactly-once ingestion,
idempotent proposals, and the policy-aware auto-apply stepping."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from controller import stats  # noqa: E402
from controller.api import ApiError  # noqa: E402
from controller.cohorts import Cohort, assign, merge_rectangles  # noqa: E402
from controller.gov import Gov  # noqa: E402
from controller.ingest import Ingestor, cell_of  # noqa: E402
from controller.store import Store  # noqa: E402


def test_binom_tail_matches_known_values():
    assert abs(stats.binom_sf(1, 10, 0.5) - (1 - 0.5 ** 10)) < 1e-9
    assert stats.binom_sf(0, 10, 0.3) == 1.0
    assert stats.binom_sf(20, 100, 0.006) < 1e-10


def test_two_prop_z_sign_and_symmetry():
    assert stats.two_prop_z(60, 100, 40, 100) > 0
    assert abs(stats.two_prop_z(60, 100, 40, 100) + stats.two_prop_z(40, 100, 60, 100)) < 1e-9


def test_ridge_pools_cells_and_is_deterministic():
    rows = [({"lang": "hi"}, 0.2, 0.01), ({"lang": "hi"}, 0.18, 0.01), ({"lang": "en"}, -0.1, 0.01), ({"lang": "en"}, -0.12, 0.01)]
    m1, m2 = stats.RidgeLogLift(), stats.RidgeLogLift()
    for m in (m1, m2):
        m.fit(rows, {"lang": ["hi", "en"]}, ["lang"])
    t1, v1 = m1.predict({"lang": "hi"})
    assert t1 == m2.predict({"lang": "hi"})[0] and t1 > 0.1 and v1 > 0
    assert m1.predict({"lang": "en"})[0] < 0


def test_cohort_ids_are_canonical_and_first_match_wins():
    a, b = Cohort({"lang": ["ta", "hi"]}), Cohort({"lang": ["hi", "ta"]})
    assert a.id == b.id == "lang=hi+ta"
    c1, c2 = Cohort({"age_band": ["60+"]}), Cohort({"lang": ["ta"]})
    assert assign([c1, c2], cell_of({"lang": "ta", "city_tier": "1", "age_band": "60+", "value_band": "low"})) == c1.id
    assert assign([c1, c2], cell_of({"lang": "en", "city_tier": "1", "age_band": "18-30", "value_band": "low"})) == "default"


def test_merge_rectangles_is_an_exact_cover():
    cells = [("hi", "60+"), ("ta", "60+"), ("hi", "18-30")]
    rects = merge_rectangles(cells, ["lang", "age_band"])
    covered = {(l, a) for r in rects for l in r["lang"] for a in r["age_band"]}
    assert covered == set(cells)


class FakeApi:
    def __init__(self):
        self.approvals, self.calls = {}, []

    def post(self, path, body):
        self.calls.append(path)
        if path == "/approvals":
            for a in self.approvals.values():
                if a["proposal_id"] == body["proposal_id"]:
                    raise ApiError(409, {"error": "duplicate_proposal_id"})
            aid = f"apr_{len(self.approvals) + 1}"
            self.approvals[aid] = {"approval_id": aid, "proposal_id": body["proposal_id"], "status": "pending"}
            return {"approval_id": aid}
        raise AssertionError(path)

    def get(self, path, **kw):
        if path == "/approvals":
            return list(self.approvals.values())
        return self.approvals[path.rsplit("/", 1)[1]]


def _body():
    return {"change_summary": "s", "diff": {"x": 1}, "affected_leads": 1, "dry_run": {"m": 1}, "impact_score": 0.2, "rationale": "r"}


def test_submit_replay_after_crash_adopts_existing_approval():
    with tempfile.TemporaryDirectory() as d:
        s, api = Store(os.path.join(d, "t.db")), FakeApi()
        g = Gov(s, api, lambda *a: None)
        cfg = {"prompt_version": "P1"}
        pid = g.submit("2027-01-04T11:00:00+05:30", "wf", "opt", 1, cfg, _body())
        # simulate: POST succeeded at the simulator but we crashed before recording it
        s.x("UPDATE proposals SET status='intent', approval_id=NULL WHERE proposal_id=?", (pid,))
        g.reconcile("2027-01-04T11:15:00+05:30", "wf", 1)
        row = s.q("SELECT status, approval_id FROM proposals WHERE proposal_id=?", (pid,))[0]
        assert row[0] == "pending" and row[1] == "apr_1"
        assert len(api.approvals) == 1            # never duplicated at the simulator


def test_new_attempt_for_same_config_gets_new_id():
    with tempfile.TemporaryDirectory() as d:
        s, api = Store(os.path.join(d, "t.db")), FakeApi()
        g = Gov(s, api, lambda *a: None)
        p1 = g.submit("t", "wf", "opt", 1, {"a": 1}, _body())
        p2 = g.submit("t", "wf", "opt", 1, {"a": 1}, _body())
        assert p1 != p2 and len(api.approvals) == 2


def _chunk(events):
    return "\n".join(json.dumps(e) for e in events)


def test_ingest_is_exactly_once_per_chunk():
    with tempfile.TemporaryDirectory() as d:
        s = Store(os.path.join(d, "t.db"))
        ing = Ingestor(s, None, lambda *a: None)
        ts = "2027-01-04T10:00:00+05:30"
        evs = [{"type": "lead", "ts": ts, "workflow_id": "w", "campaign_id": "c", "lead_id": "w:l1", "person_id": "p",
                "features": {"lang": "hi", "city_tier": "1", "age_band": "60+", "value_band": "low"}, "event_id": 1},
               {"type": "call", "ts": ts, "workflow_id": "w", "lead_id": "w:l1", "config_version": 1, "cohort_id": "default",
                "variant": {"welcome_message": "W1", "voice": "V1", "caller_id": "D1", "prompt_version": "P1"},
                "connected": True, "engaged": True, "qa": {"hallucination_flag": False, "flow_adherence": 0.9}, "event_id": 2}]
        ing._ingest_chunk("events", 0, _chunk(evs))
        ing._ingest_chunk("events", 0, _chunk(evs))      # replayed chunk (restart): event_id floor makes it a no-op
        assert s.q("SELECT SUM(dials),SUM(conn),SUM(eng) FROM agg_var")[0] == (1, 1, 1)
        assert s.kget("cursor:events") == 0
