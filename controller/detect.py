"""Population-level detectors. Every detector needs a minimum sample and a significance level AND a minimum
relative effect, so one bad call (or one noisy hour) never triggers anything."""
import math
from collections import defaultdict

from . import stats
from .cohorts import assign
from .planner import kpi


def did_status(store, wf, now_hb, dids, min_n=150):
    """Per caller ID: recent pickup vs (a) its own earlier baseline and (b) its peers in the same window."""
    out = {}
    for span in (3, 6, 12):
        lo = now_hb - span + 1
        rows = {r[0]: (r[1], r[2]) for r in store.q(
            "SELECT did,SUM(dials),SUM(conn) FROM agg_did WHERE wf=? AND hb>=? GROUP BY did", (wf, lo))}
        hrs = sorted({h % 24 for h in range(lo, now_hb + 1)})
        qm = ",".join("?" * len(hrs))
        # baseline restricted to the same hours of day: pickup has a daily profile, so a 3h afternoon window must not be
        # compared against an all-day average
        base = {r[0]: (r[1], r[2]) for r in store.q(
            f"SELECT did,SUM(dials),SUM(conn) FROM agg_did WHERE wf=? AND hb<? AND ((hb%24)+24)%24 IN ({qm}) GROUP BY did",
            (wf, lo, *hrs))}
        res = {}
        for d in dids:
            n, k = rows.get(d, (0, 0))
            if n < min_n:
                continue
            peers = [(rows[o][0], rows[o][1]) for o in rows if o != d and rows[o][0] >= 30]
            pn, pk = sum(p[0] for p in peers), sum(p[1] for p in peers)
            bn, bk = base.get(d, (0, 0))
            zb = stats.two_prop_z(k, n, bk, bn) if bn >= 300 else None
            zp = stats.two_prop_z(k, n, pk, pn) if pn >= min_n else None
            rate = k / n
            rel_b = rate / (bk / bn) - 1 if bn >= 300 and bk else None
            rel_p = rate / (pk / pn) - 1 if pn >= min_n and pk else None
            bad_b = zb is not None and zb <= -4.0 and rel_b <= -0.25
            bad_p = zp is not None and zp <= -3.0 and rel_p <= -0.15
            # flag when it is worse than its own past AND worse than peers (or has no peers / no past to compare with)
            if bad_b and (bad_p or zp is None):
                flag = True
            elif bad_p and bn < 300:
                flag = True
            else:
                flag = False
            res[d] = {"span_h": span, "dials": n, "pickup": round(rate, 4), "baseline_pickup": round(bk / bn, 4) if bn else None,
                      "peer_pickup": round(pk / pn, 4) if pn else None, "z_base": None if zb is None else round(zb, 2),
                      "z_peer": None if zp is None else round(zp, 2), "flagged": flag}
        for d, r in res.items():
            if d not in out or r["flagged"]:
                out[d] = r
        if any(r["flagged"] for r in res.values()):
            break
    return out


def hallucination_status(store, wf, prompt, now_hb, since_hb, changed=False):
    base = store.q("SELECT SUM(conn),SUM(halluc) FROM agg_prompt WHERE wf=? AND hb<0", (wf,))[0]
    p0 = (base[1] or 0) / base[0] if base[0] else 0.006
    p0 = max(p0, 0.004)
    lo = max(since_hb, now_hb - 47)
    n, k, flow = store.q("SELECT SUM(conn),SUM(halluc),SUM(flow) FROM agg_prompt WHERE wf=? AND p=? AND hb>=?",
                         (wf, prompt, lo))[0]
    n, k, flow = n or 0, k or 0, flow or 0.0
    pv = stats.binom_sf(k, n, p0) if n else 1.0
    rate = k / n if n else 0.0
    return {"prompt": prompt, "n": n, "flags": k, "rate": round(rate, 4), "baseline": round(p0, 4), "p_value": pv,
            "spike": bool((n >= 40 and k >= 4 and rate >= 1.75 * p0 and pv < 1e-3) if changed
                      else (n >= 80 and k >= 4 and rate >= 1.75 * p0 and pv < 1e-4)), "since_hb": lo}


def kpi_drift(store, wf, info, now_hb, recent_h=24, base_h=24 * 7):
    """Workflow-level drift of the primary and guardrail KPI: last 24h vs the preceding week."""
    prim, (pn, pd), gname, (gn, gd) = kpi(info)
    col = {"dials": "dials", "conn": "conn", "eng": "eng"}
    res = {}
    for name, (num, den) in ((prim, (pn, pd)), (gname, (gn, gd))):
        r = store.q(f"SELECT SUM({num}),SUM({den}) FROM agg_prompt WHERE wf=? AND hb>?", (wf, now_hb - recent_h))[0]
        b = store.q(f"SELECT SUM({num}),SUM({den}) FROM agg_prompt WHERE wf=? AND hb<=? AND hb>?",
                    (wf, now_hb - recent_h, now_hb - recent_h - base_h))[0]
        k1, n1, k0, n0 = (r[0] or 0), (r[1] or 0), (b[0] or 0), (b[1] or 0)
        if n1 < 300 or n0 < 1000:
            res[name] = None
            continue
        z = stats.two_prop_z(k1, n1, k0, n0)
        rel = (k1 / n1) / (k0 / n0) - 1
        res[name] = {"recent": round(k1 / n1, 4), "baseline": round(k0 / n0, 4), "rel": round(rel, 4), "z": round(z, 2),
                     "drift": bool(z <= -4.0 and rel <= -0.08), "n": n1}
    return res


def cohort_kpis(store, wf, info, cohorts, now_tb, recent_tb=4, base_tb=24):
    """Per shared Cohort object: primary KPI recent vs baseline. Used by the supervisor view and drift alerts."""
    prim, (pn, pd), gname, (gn, gd) = kpi(info)
    idx = {"dials": 0, "conn": 1, "eng": 2}
    rows = store.q("SELECT tb,cell,SUM(dials),SUM(conn),SUM(eng) FROM agg_var WHERE wf=? AND tb>? GROUP BY tb,cell",
                   (wf, now_tb - recent_tb - base_tb))
    acc = defaultdict(lambda: {"r": [0, 0, 0], "b": [0, 0, 0]})
    for tb, cell, d, c, e in rows:
        cid = assign(cohorts, cell)
        side = "r" if tb > now_tb - recent_tb else "b"
        a = acc[cid][side]
        a[0] += d; a[1] += c; a[2] += e
    out = {}
    for cid, a in acc.items():
        def rate(side):
            v = a[side]
            num, den = v[idx[pn]], v[idx[pd]]
            return (num / den, den) if den else (None, 0)
        r, rn = rate("r"); b, bn = rate("b")
        out[cid] = {"recent": None if r is None else round(r, 4), "baseline": None if b is None else round(b, 4),
                    "n_recent": rn, "n_base": bn}
    return out
