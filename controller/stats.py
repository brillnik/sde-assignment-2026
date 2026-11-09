"""Deterministic statistics (no randomness anywhere in winner selection)."""
import math

import numpy as np


def norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def binom_sf(k, n, p):
    """P(X >= k) for X~Bin(n,p): exact via log-pmf summation (n is at most a few thousand here)."""
    if k <= 0:
        return 1.0
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    lg = math.lgamma
    tot = 0.0
    for i in range(k, n + 1):
        t = lg(n + 1) - lg(i + 1) - lg(n - i + 1) + i * lp + (n - i) * lq
        v = math.exp(t)
        tot += v
        if v < 1e-14 * tot and i > n * p + 5:
            break
    return min(1.0, tot)


def two_prop_z(k1, n1, k0, n0):
    """z for rate1 - rate0 (pooled). Returns 0 if undefined."""
    if n1 < 1 or n0 < 1:
        return 0.0
    p = (k1 + k0) / (n1 + n0)
    se = math.sqrt(max(p * (1 - p), 1e-12) * (1 / n1 + 1 / n0))
    return (k1 / n1 - k0 / n0) / se


def rate_se(k, n):
    p = (k + 0.5) / (n + 1)
    return math.sqrt(p * (1 - p) / max(n, 1))


def log_ratio(kv, nv, kr, nr):
    """log(rate_v/rate_r) with a +0.5 smoothing and delta-method variance of the log ratio."""
    pv, pr = (kv + 0.5) / (nv + 1), (kr + 0.5) / (nr + 1)
    var = (1 - pv) / (kv + 0.5) + (1 - pr) / (kr + 0.5)
    return math.log(pv / pr), var


class RidgeLogLift:
    """Weighted ridge regression of per-cell log-lifts on one-hot feature levels.

    y_s = log(rate_v,s / rate_ref,s) is observed per segment cell with variance var_s. Model: y = X b where X has an
    intercept plus one-hot columns for each feature level; feature coefficients carry a N(0, tau^2) prior (partial
    pooling - sparse cells borrow strength from the same feature level elsewhere), the intercept a wide prior.
    Posterior mean/variance of any cell's lift is then closed-form => deterministic z-scores."""

    def __init__(self, tau=0.12):
        self.tau = tau

    def fit(self, rows, levels, feats):
        """rows: list of (cell_feature_dict, y, var). levels: {feature: [values]}. feats: features included."""
        cols = [("1", None)]
        for f in feats:
            for v in levels[f]:
                cols.append((f, v))
        self.cols, self.feats = cols, feats
        X = np.array([self._x(r[0]) for r in rows]) if rows else np.zeros((0, len(cols)))
        y = np.array([r[1] for r in rows])
        w = np.array([1.0 / max(r[2], 1e-6) for r in rows])
        lam = np.array([1e-2] + [1.0 / self.tau ** 2] * (len(cols) - 1))
        A = X.T @ (X * w[:, None]) + np.diag(lam)
        self.cov = np.linalg.inv(A)
        self.beta = self.cov @ (X.T @ (w * y))

    def _x(self, feat):
        return [1.0 if c[0] == "1" else (1.0 if feat.get(c[0]) == c[1] else 0.0) for c in self.cols]

    def predict(self, feat):
        x = np.array(self._x(feat))
        return float(x @ self.beta), float(x @ self.cov @ x)

    def coef_z(self):
        out = {}
        for i, (f, v) in enumerate(self.cols):
            if f != "1":
                out[(f, v)] = float(self.beta[i] / math.sqrt(max(self.cov[i, i], 1e-12)))
        return out


def g_test_heterogeneity(table):
    """Chi-square statistic for homogeneity of hour profiles across groups. table: 2D counts (groups x hours).
    Returns (chi2, dof)."""
    t = np.asarray(table, dtype=float)
    t = t[t.sum(1) > 0][:, t.sum(0) > 0]
    if t.shape[0] < 2 or t.shape[1] < 2:
        return 0.0, 0
    exp = np.outer(t.sum(1), t.sum(0)) / t.sum()
    chi = float(((t - exp) ** 2 / exp).sum())
    return chi, (t.shape[0] - 1) * (t.shape[1] - 1)


def chi2_z(chi, dof):
    """Wilson-Hilferty normal approximation -> z equivalent for a chi-square upper tail."""
    if dof <= 0:
        return 0.0
    return ((chi / dof) ** (1 / 3) - (1 - 2 / (9 * dof))) / math.sqrt(2 / (9 * dof))
