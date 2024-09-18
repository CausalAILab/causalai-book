import itertools
import math
from typing import Dict, List

import pandas as pd
import sympy as sp


class SymbolicSCM:
    def __init__(
        self,
        f: Dict[sp.Symbol, sp.Expr],
        pu: Dict[sp.Symbol, List],
    ):
        assert all(isinstance(k, sp.Symbol) for k in f), f
        assert all(isinstance(k, sp.Symbol) for k in pu), pu
        assert all(
            (
                isinstance(v, list)
                and math.isclose(sum(v), 1)
                and all(0 <= v[i] <= 1 for i in range(len(v)))
            )
            or (isinstance(v, float) and 0 <= v <= 1)
            for v in pu.values()
        ), pu

        self.v = list(f)
        self.u = list(pu)
        self.f = {k: sp.sympify(v) for k, v in f.items()}

        self.pu_domains = {
            k: (
                [False, True]
                if isinstance(v, float)
                else [i for i in range(len(v)) if v[i]]
            )
            for k, v in pu.items()
        }
        self.pu = {k: v if isinstance(v, list) else [1 - v, v] for k, v in pu.items()}

    def _evaluate(self, u):
        assert {isinstance(k, sp.Symbol) for k in u}, u
        assert {isinstance(v, int) for v in u.values()}, u
        assert set(u) == set(self.pu), (u, self.pu)

        v = dict(u)
        for k in self.f:
            v[k] = self.f[k].subs(v)
        return v

    def get_probability_table(self, symbols=None, u=False):
        if symbols is None:
            if u:
                symbols = self.u + self.v
            else:
                symbols = self.v

        settings = [[(k, i) for i in v] for k, v in self.pu_domains.items()]
        records = []
        for u in map(dict, itertools.product(*settings)):
            records.append(
                {
                    k: hash(v) if v in [sp.false, sp.true] else int(v)
                    for k, v in self._evaluate(u).items()
                }
            )
            records[-1]["probability"] = math.exp(
                sum(math.log(self.pu[k][u[k]]) for k in self.u)
            )

        return pd.DataFrame(records).groupby(symbols).probability.sum().reset_index()

    def query(self, x, given={}):
        assert all(k in self.v for k in x), x
        assert all(k in self.v for k in given), given

        # could be relaxed
        assert set(x).isdisjoint(given), (x, given)

        if given:
            return self.query({**x, **given}) / self.query(given)

        pt = self.get_probability_table()
        query = " and ".join(f"{str(k)} == {str(x[k])}" for k in x)
        return pt.query(query).probability.sum()

    def do(self, x):
        assert all(k in self.v for k in x), x
        return SymbolicSCM(
            f={k: sp.sympify(x[k]) if k in x else v for k, v in self.f.items()},
            pu=self.pu,
        )
