"""The one shared Cohort object. Detection, experiments, call-time tables, proposals and the supervisor view all
refer to cohorts by this id; the id is canonical over the `where` clause, so "seniors in Tamil" is one thing."""
from .ingest import FEATURES, cell_features


class Cohort:
    def __init__(self, where, cid=None):
        self.where = {f: tuple(sorted(v)) for f, v in where.items() if v}
        self.id = cid or self.canonical(self.where)

    @staticmethod
    def canonical(where):
        if not where:
            return "default"
        return "&".join(f"{f}={'+'.join(sorted(v))}" for f, v in sorted(where.items()))

    def matches(self, feat):
        return all(feat.get(f) in v for f, v in self.where.items())

    def matches_cell(self, cell):
        return self.matches(cell_features(cell))

    def to_cfg(self):
        return {"id": self.id, "where": {f: list(v) for f, v in self.where.items()}}

    @classmethod
    def from_cfg(cls, c):
        return cls(c["where"], c["id"])


def assign(cohorts, cell):
    """First-match semantics, identical to the simulator's contract."""
    feat = cell_features(cell)
    for c in cohorts:
        if c.matches(feat):
            return c.id
    return "default"


def merge_rectangles(cells, feats):
    """Exactly cover a set of projected cells (tuples over `feats`) with few `where` rectangles.
    Groups by first feature the set of second-feature values, then merges identical rows."""
    if not feats:
        return [{}]
    if len(feats) == 1:
        return [{feats[0]: sorted({c[0] for c in cells})}]
    rows = {}
    for c in cells:
        rows.setdefault(c[0], set()).add(c[1:])
    by_rest = {}
    for v0, rest in rows.items():
        by_rest.setdefault(frozenset(rest), []).append(v0)
    out = []
    for rest, v0s in by_rest.items():
        for sub in merge_rectangles(sorted(rest), feats[1:]):
            w = {feats[0]: sorted(v0s)}
            w.update(sub)
            out.append(w)
    return out
