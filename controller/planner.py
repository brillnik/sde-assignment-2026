"""Learning core: turns aggregates into (a) a cohort partition, (b) per-cohort allocation plans for welcome message
and voice, (c) per-cohort hour weights, and (d) decay / harm checks on live winners.

Everything here is deterministic: closed-form z-scores from a ridge-pooled log-lift model, no sampling."""
import copy
import math
from statistics import NormalDist
from collections import defaultdict

import numpy as np

from . import stats
from .cohorts import Cohort, assign, merge_rectangles
from .ingest import FEATURES, cell_features

DIMS = ("welcome_message", "voice")
Z_WIN = 2.2          # one-sided z for a challenger to beat the reference by >= MIN_LIFT in a cohort cell
Z_AVOID = 2.5        # one-sided z for dropping a clearly worse variant from exploration
FWER = 0.30          # family-wise false-winner target per evaluation window
MIN_LIFT = 0.02      # relative lift that is worth a customer-facing change
MIN_COHORT_SHARE = 0.03
MAX_COHORTS = 12
WIN_SHARE, REF_SHARE_WIN = 0.65, 0.20
IDX = {"dials": 4, "conn": 5, "eng": 6}   # column positions in window_rows()
WINDOW_TBS = 20      # analysis window: 5 days of 6h buckets (adapts to decaying winners)


def kpi(info):
    """(numerator, denominator) columns of the primary and guardrail KPI."""
    prim = info["objective"]["primary"]
    cols = {"engagement_rate": ("eng", "conn"), "pickup_rate": ("conn", "dials")}
    other = "pickup_rate" if prim == "engagement_rate" else "engagement_rate"
    return prim, cols[prim], other, cols[other]


def tv(a, b):
    keys = set(a) | set(b)
    sa, sb = sum(a.values()) or 1, sum(b.values()) or 1
    return 0.5 * sum(abs(a.get(k, 0) / sa - b.get(k, 0) / sb) for k in keys)


def norm(d):
    s = sum(d.values())
    return {k: round(v / s, 4) for k, v in d.items() if v > 0}


class Planner:
    def __init__(self, store, log=print):
        self.s, self.log = store, log

    # ------------------------------------------------------------------ data access
    def window_rows(self, wf, since_tb, until_tb=None, ver_min=None):
        sql = "SELECT cell,w,v,p,SUM(dials),SUM(conn),SUM(eng) FROM agg_var WHERE wf=? AND tb>=?"
        args = [wf, since_tb]
        if until_tb is not None:
            sql += " AND tb<?"; args.append(until_tb)
        if ver_min is not None:
            sql += " AND ver>=?"; args.append(ver_min)
        sql += " GROUP BY cell,w,v,p"
        return self.s.q(sql, args)

    # ------------------------------------------------------------------ hour heterogeneity (call time)
    def hour_tables(self, wf, since_day):
        rows = self.s.q("SELECT hour,cell,SUM(dials),SUM(conn),SUM(eng) FROM agg_hour WHERE wf=? AND day>=? GROUP BY hour,cell",
                        (wf, since_day))
        return rows

    def hour_importance(self, rows):
        """z-equivalent of how much each feature's hour-profile differs between its values (multiplicative null)."""
        out = {}
        hours = sorted({r[0] for r in rows})
        for f in FEATURES:
            vals = sorted({cell_features(r[1])[f] for r in rows})
            if len(vals) < 2 or len(hours) < 2:
                continue
            D = np.zeros((len(vals), len(hours))); C = np.zeros_like(D)
            for h, cell, d, c, e in rows:
                D[vals.index(cell_features(cell)[f]), hours.index(h)] += d
                C[vals.index(cell_features(cell)[f]), hours.index(h)] += c
            if D.sum() < 2000:
                continue
            a = np.ones(len(vals)); b = np.ones(len(hours))
            for _ in range(30):
                b = C.sum(0) / np.maximum((D * a[:, None]).sum(0), 1e-9)
                a = C.sum(1) / np.maximum((D * b[None, :]).sum(1), 1e-9)
            E = np.clip(D * a[:, None] * b[None, :], 1e-6, None)
            pr = np.clip(E / np.maximum(D, 1), 1e-6, 0.999)
            chi = float((((C - E) ** 2) / (E * (1 - pr))).sum())
            out[f] = stats.chi2_z(chi, (len(vals) - 1) * (len(hours) - 1))
        return out

    def hour_weights(self, rows, cohorts, window, k0=40.0, gamma=1.5):
        """Per cohort: weight_h ~ (cohort pickup in hour h / cohort mean)^gamma, mean-normalised, clipped, all window hours."""
        groups = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for h, cell, d, c, e in rows:
            cid = assign(cohorts, cell)
            g = groups[cid][h]
            g[0] += d; g[1] += c
        out = {}
        for cid, hh in groups.items():
            D = sum(v[0] for v in hh.values()); Cn = sum(v[1] for v in hh.values())
            if D < 300:
                continue
            rbar = Cn / D
            w = {}
            for h in range(window[0], window[1]):
                d, c = hh.get(h, (0, 0))
                r = (c + k0 * rbar) / (d + k0)
                w[h] = (r / max(rbar, 1e-6)) ** gamma
            m = sum(w.values()) / len(w)
            out[cid] = {str(h): round(min(3.0, max(0.35, v / m)), 3) for h, v in w.items()}
        return out

    def design_effect(self, wf, since_tb, info, dim, ref):
        """Empirical variance inflation (dials are not independent: engaged leads leave the pool, attempts cluster by
        lead). Placebo contrast: the *reference* arm split by day parity should show no difference, so
        phi = mean(y^2)/mean(var) over cells measures how much larger the real variance is than the binomial one."""
        _, (num, den), _, _ = kpi(info)
        col = {"welcome_message": "w", "voice": "v"}[dim]
        rows = self.s.q(f"SELECT cell,(tb/4)%2,SUM({num}),SUM({den}) FROM agg_var WHERE wf=? AND tb>=? AND {col}=? "
                        f"GROUP BY cell,(tb/4)%2", (wf, since_tb, ref))
        by = defaultdict(dict)
        for cell, par, k, n in rows:
            by[cell][par] = (k or 0, n or 0)
        tk = sum(v[0] for d in by.values() for v in d.values()); tn = sum(v[1] for d in by.values() for v in d.values())
        p0 = tk / tn if tn else None
        ys, vs = [], []
        for cell, d in by.items():
            if 0 in d and 1 in d and d[0][1] >= 30 and d[1][1] >= 30:
                y, v = stats.log_ratio(d[0][0], d[0][1], d[1][0], d[1][1], p0)
                ys.append(y * y); vs.append(v)
        if len(ys) < 5:
            return 1.5
        return float(min(4.0, max(1.0, sum(ys) / sum(vs))))

    # ------------------------------------------------------------------ variant lift model
    def fit_dim(self, rows, dim, ref, info, feats, options, phi=1.0):
        """For every non-ref variant of `dim`: ridge log-lift model over cells. Returns {variant: model} plus levels."""
        _, (num, den), _, _ = kpi(info)
        idx = {"num": IDX[num], "den": IDX[den]}
        j = {"welcome_message": 1, "voice": 2}[dim]
        cnt = defaultdict(lambda: [0, 0])            # (cell, variant) -> [k, n]
        for r in rows:
            c = cnt[(r[0], r[j])]
            c[0] += r[idx["num"]]; c[1] += r[idx["den"]]
        cells = sorted({k[0] for k in cnt})
        levels = {f: sorted({cell_features(c)[f] for c in cells}) for f in FEATURES}
        tot_k = sum(c[0] for c in cnt.values()); tot_n = sum(c[1] for c in cnt.values())
        p0 = tot_k / tot_n if tot_n else None
        models, vol = {}, defaultdict(float)
        for (cell, v), (k, n) in cnt.items():
            vol[cell] += n
        for v in options:
            if v == ref:
                continue
            data = []
            for cell in cells:
                kv, nv = cnt.get((cell, v), (0, 0))
                kr, nr = cnt.get((cell, ref), (0, 0))
                if nv >= 5 and nr >= 5:      # tiny cells are fine: variance (outcome-independent) gives them low weight
                    y, var = stats.log_ratio(kv, nv, kr, nr, p0)
                    data.append((cell_features(cell), y, var * phi))
            if len(data) < 4:
                continue
            m = stats.RidgeLogLift()
            m.fit(data, levels, list(feats))
            models[v] = m
        return models, levels, cnt, vol

    def importance(self, rows, info, state, options):
        """Max |coef z| per feature across both dims and all variants (full-feature fit)."""
        imp = defaultdict(float)
        for dim in DIMS:
            models, *_ = self.fit_dim(rows, dim, state["ref"][dim], info, FEATURES, options[dim])
            for v, m in models.items():
                for (f, val), z in m.coef_z().items():
                    imp[f] = max(imp[f], abs(z))
        return dict(imp)

    # ------------------------------------------------------------------ the plan
    def plan(self, wf, info, state, now_tb, live_cfg, ver_min=None):
        """Returns dict(partition feats, cohorts, per-cohort plans, hour weights, theta lookup, analysis summary)."""
        options = info["options"]
        since = max(state.get("regime_tb", -10 ** 6), now_tb - WINDOW_TBS)
        rows = self.window_rows(wf, since, ver_min=ver_min)
        prompt_rows = rows
        # importance of features for experiments & for call-time
        imp_exp = self.importance(prompt_rows, info, state, options)
        hrows = self.hour_tables(wf, now_tb // 4 - 21)
        imp_hr = {f: z for f, z in self.hour_importance(hrows).items() if z >= 4.0}
        imp = defaultdict(float)
        for f, z in imp_exp.items():
            if z >= 2.0:
                imp[f] = max(imp[f], z)
        for f, z in imp_hr.items():
            imp[f] = max(imp[f], z)
        feats = [f for f, _ in sorted(imp.items(), key=lambda kv: -kv[1])][:2]
        feats = [f for f in FEATURES if f in feats]       # canonical order

        # projected cells, volumes
        dials_by_cell = defaultdict(float)
        for r in rows:
            dials_by_cell[r[0]] += r[4]
        if not dials_by_cell:
            for h, cell, d, c, e in hrows:
                dials_by_cell[cell] += d
        proj_vol = defaultdict(float)
        for cell, d in dials_by_cell.items():
            fe = cell_features(cell)
            proj_vol[tuple(fe[f] for f in feats)] += d
        total = sum(proj_vol.values()) or 1.0

        # per-dim models on the projected features; predictions per projected cell
        theta = {}                 # (dim, variant, projected cell) -> (theta, var)
        phi = {}
        analysis = {}
        for dim in DIMS:
            ref = state["ref"][dim]
            phi[dim] = self.design_effect(wf, since, info, dim, ref)
            models, levels, cnt, vol = self.fit_dim(prompt_rows, dim, ref, info, feats, options[dim], phi[dim])
            analysis[dim] = {"ref": ref, "variants": {}, "design_effect": round(phi[dim], 2)}
            for v, m in models.items():
                for pc in proj_vol:
                    fe = dict(zip(feats, pc))
                    theta[(dim, v, pc)] = m.predict(fe)
                n_all = sum(cnt[(c, v)][1] for c in {k[0] for k in cnt} if (c, v) in cnt)
                k_all = sum(cnt[(c, v)][0] for c in {k[0] for k in cnt} if (c, v) in cnt)
                n_ref = sum(cnt[(c, ref)][1] for c in {k[0] for k in cnt} if (c, ref) in cnt)
                k_ref = sum(cnt[(c, ref)][0] for c in {k[0] for k in cnt} if (c, ref) in cnt)
                if n_all and n_ref:
                    y, var = stats.log_ratio(k_all, n_all, k_ref, n_ref)
                    analysis[dim]["variants"][v] = {"n": n_all, "rate": k_all / n_all, "ref_n": n_ref, "ref_rate": k_ref / n_ref,
                                                    "pooled_lift": round(math.exp(y) - 1, 4), "se": round(math.sqrt(var), 4)}
            # variants with no data yet
            for v in options[dim]:
                if v != ref and v not in analysis[dim]["variants"]:
                    analysis[dim]["variants"][v] = {"n": 0}
        # recency confirmation: a winner must also win in the most recent 2 days (catches decaying variants)
        rec_tbs = 8
        theta_rec = {}
        if now_tb - rec_tbs > since:
            rrows = self.window_rows(wf, now_tb - rec_tbs)
            for dim in DIMS:
                models, *_ = self.fit_dim(rrows, dim, state["ref"][dim], info, feats, options[dim], phi.get(dim, 1.5))
                for v, m in models.items():
                    for pc in proj_vol:
                        theta_rec[(dim, v, pc)] = m.predict(dict(zip(feats, pc)))
        # guardrail screen (pooled, per variant)
        blocked = self.guardrail_blocked(wf, info, state, rows, options)

        # Family-wise control: the bar grows with the number of (variant x projected cell) comparisons made and with the
        # number of daily looks accumulated in the window (repeated looking inflates false winners).
        m_tests = max(1, sum(1 for k in theta))
        looks = max(1.0, (now_tb - since) / 4.0)
        z_win = min(3.6, max(Z_WIN, NormalDist().inv_cdf(1 - FWER / (m_tests * math.sqrt(looks)))))
        for dim in DIMS:
            analysis[dim]["z_win"] = round(z_win, 2)
        live_cohorts = [Cohort.from_cfg(c) for c in live_cfg.get("cohorts", [])]

        def incumbent(dim, pc):
            """The variant already carrying >=60% of this cell's traffic in the live config (a promoted winner)."""
            fe = dict(zip(feats, pc))
            cid = next((c.id for c in live_cohorts if c.matches(fe)), "default")
            al = live_cfg.get("allocations", {})
            dist = (al.get(cid, {}).get(dim)) or (al.get("default", {}).get(dim)) or {}
            if not dist:
                return None
            top = max(dist, key=dist.get)
            return top if dist[top] / (sum(dist.values()) or 1) >= 0.6 and top != state["ref"][dim] else None

        bans = state.get("bans", {})
        plan_by_pc = {}
        for pc in proj_vol:
            plans = {}
            for dim in DIMS:
                ref = state["ref"][dim]
                cands, avoid, lcbs = [], set(), {}
                for v in options[dim]:
                    if v == ref:
                        continue
                    if v in bans.get(dim, {}) or v in blocked.get(dim, set()):
                        avoid.add(v); continue
                    th = theta.get((dim, v, pc))
                    if not th:
                        continue
                    t, var = th
                    se = math.sqrt(var)
                    if theta_rec:
                        tr = theta_rec.get((dim, v, pc))
                        if not tr:
                            continue          # no recent evidence for this arm: cannot confirm
                        tr_t, tr_var = tr
                        if tr_t - 1.28 * math.sqrt(tr_var) <= 0:
                            if tr_t + Z_AVOID * math.sqrt(tr_var) < 0:
                                avoid.add(v)
                            continue
                        t = min(t, tr_t)      # be conservative: promised lift is the smaller of full-window and recent
                    inc = incumbent(dim, pc) == v
                    # hysteresis: keeping a promoted winner needs only a 90% lower bound > 0 (decay is caught separately);
                    # promoting a new one needs the full family-wise bar
                    if (t - 1.28 * se > 0) if inc else (t - z_win * se > math.log(1 + MIN_LIFT)):
                        cands.append((t, v, se))
                    elif t + Z_AVOID * se < 0:
                        avoid.add(v)
                if cands:
                    t, v, se = max(cands)
                    plans[dim] = ("win", v, round(t, 4), round(se, 4), tuple(sorted(avoid)))
                else:
                    plans[dim] = ("explore", None, 0, 0, tuple(sorted(avoid)))
            plan_by_pc[pc] = plans

        key = lambda pl: tuple((pl[d][0], pl[d][1]) for d in DIMS)     # avoid-sets alone must not create/destroy cohorts
        vol_by_key = defaultdict(float)
        for pc, pl in plan_by_pc.items():
            vol_by_key[key(pl)] += proj_vol[pc]
        default_key = max(vol_by_key, key=vol_by_key.get)
        cells_by_key = defaultdict(list)
        for pc, pl in plan_by_pc.items():
            k = key(pl)
            if k != default_key and proj_vol[pc] / total < MIN_COHORT_SHARE / 2:
                k = default_key                       # too small to deserve its own cohort: fold into default
            cells_by_key[k].append(pc)
        cohorts, cohort_plans = [], {}
        default_plan = next(plan_by_pc[pc] for pc in plan_by_pc if key(plan_by_pc[pc]) == default_key)
        nondefault = [(k, c) for k, c in cells_by_key.items() if k != default_key]
        nondefault.sort(key=lambda kc: -sum(proj_vol[p] for p in kc[1]))
        for k, pcs in nondefault:
            if sum(proj_vol[p] for p in pcs) / total < MIN_COHORT_SHARE:
                continue
            for where in merge_rectangles(sorted(pcs), feats):
                if len(cohorts) >= MAX_COHORTS:
                    break
                c = Cohort(where)
                cohorts.append(c)
                cohort_plans[c.id] = plan_by_pc[pcs[0]]
        hours = self.hour_weights(hrows, cohorts, tuple(info["dialling_window"])) if (imp_hr and cohorts) or imp_hr else {}
        return {"feats": feats, "cohorts": cohorts, "cohort_plans": cohort_plans, "default_plan": default_plan,
                "hours": hours, "hour_importance": imp_hr, "theta": theta, "proj_vol": dict(proj_vol),
                "analysis": analysis, "importance": dict(imp), "blocked": {d: sorted(v) for d, v in blocked.items()},
                "window_tbs": [since, now_tb]}

    def guardrail_blocked(self, wf, info, state, rows, options):
        """A variant that costs the guardrail KPI more than half the allowed drop (significantly) is blocked."""
        _, _, gname, (gnum, gden) = kpi(info)
        gmax = list(info["objective"]["guardrail"].values())[0]
        idx = IDX
        blocked = defaultdict(set)
        for dim, j in (("welcome_message", 1), ("voice", 2)):
            agg = defaultdict(lambda: [0, 0])
            for r in rows:
                a = agg[r[j]]
                a[0] += r[idx[gnum]]; a[1] += r[idx[gden]]
            ref = state["ref"][dim]
            if ref not in agg or agg[ref][1] < 200:
                continue
            kr, nr = agg[ref]
            for v, (kv, nv) in agg.items():
                if v == ref or nv < 200:
                    continue
                z = stats.two_prop_z(kv, nv, kr, nr)
                if (kv / nv - kr / nr) < -0.5 * gmax and z < -1.64:
                    blocked[dim].add(v)
        return blocked

    # ------------------------------------------------------------------ allocation synthesis
    @staticmethod
    def alloc_from_plan(plan, dim, ref, options):
        kind, v, _, _, avoid = plan[dim]
        others = [o for o in options if o != ref and o not in avoid]
        if kind == "win":
            rest = [o for o in others if o != v]
            d = {v: WIN_SHARE, ref: REF_SHARE_WIN}
            if rest:
                for o in rest:
                    d[o] = (1 - WIN_SHARE - REF_SHARE_WIN) / len(rest)
            else:
                d[v] += 1 - WIN_SHARE - REF_SHARE_WIN
            return norm(d)
        if not others:
            return {ref: 1.0}
        ref_share = 0.75 if len(options) <= 3 else 0.7
        d = {ref: ref_share}
        for o in others:
            d[o] = (1 - ref_share) / len(others)
        return norm(d)

    def synthesize(self, live_cfg, plan, info, state, hold_dims):
        cfg = copy.deepcopy(live_cfg)
        options = info["options"]
        cohorts = plan["cohorts"]
        sup = state.get("sup_set", {})      # distributions a client supervisor chose: only evidence of a *win* may change them
        cfg["cohorts"] = [c.to_cfg() for c in cohorts]
        alloc = cfg.setdefault("allocations", {})
        dflt = alloc.setdefault("default", {})
        newalloc = {"default": dict(dflt)}
        for dim in DIMS:
            if dim in hold_dims or (dim in sup and plan["default_plan"][dim][0] != "win"):
                newalloc["default"][dim] = dflt.get(dim)
            else:
                newalloc["default"][dim] = self.alloc_from_plan(plan["default_plan"], dim, state["ref"][dim], options[dim])
        for c in cohorts:
            pl = plan["cohort_plans"][c.id]
            e = {}
            for dim in DIMS:
                if dim in hold_dims or (dim in sup and pl[dim][0] != "win"):
                    if dflt.get(dim) is not None and dim in sup:
                        e[dim] = dflt[dim]
                    continue
                e[dim] = self.alloc_from_plan(pl, dim, state["ref"][dim], options[dim])
            if e:
                newalloc[c.id] = e
        cfg["allocations"] = newalloc
        if "schedule" not in hold_dims:
            sched = cfg.setdefault("schedule", {"hour_weights": {}, "lead_preferred_hour": {}})
            if plan["hours"]:
                hw = dict(plan["hours"])
                # leads of cohorts w/o enough data fall through to the default table; make sure one exists
                if "default" not in hw:
                    w0 = info["dialling_window"]
                    hw["default"] = {str(h): 1.0 for h in range(w0[0], w0[1])}
                sched["hour_weights"] = hw
        return cfg

    # ------------------------------------------------------------------ dry run / impact
    def expected_rel(self, cfg, plan, info, state, cell_vol):
        """Model-based expected relative KPI of a config vs. all-reference, per cohort cell and in total.
        Returns (value, var) where value = sum_cell share * E[exp(theta_w)] * E[exp(theta_v)]."""
        theta, feats = plan["theta"], plan["feats"]
        cohorts = [Cohort.from_cfg(c) for c in cfg.get("cohorts", [])]
        total = sum(cell_vol.values()) or 1.0
        val, var = 0.0, 0.0
        for cell, vol in cell_vol.items():
            cid = assign(cohorts, cell)
            fe = cell_features(cell)
            pc = tuple(fe[f] for f in feats)
            a = cfg["allocations"]
            ent = a.get(cid, {})
            prod, v_ = 1.0, 0.0
            for dim in DIMS:
                dist = ent.get(dim) or a["default"].get(dim) or {}
                s = sum(dist.values()) or 1
                e, vv = 0.0, 0.0
                for v, w in dist.items():
                    t, tv_ = theta.get((dim, v, pc), (0.0, 0.0)) if v != state["ref"][dim] else (0.0, 0.0)
                    e += (w / s) * math.exp(t)
                    vv += ((w / s) * math.exp(t)) ** 2 * tv_
                prod *= e
                v_ += vv
            share = vol / total
            val += share * prod
            var += share ** 2 * v_ * prod ** 2
        return val, var
