import itertools
import math
from typing import Dict, List

import pandas as pd
import sympy as sp
from IPython.display import Latex


class SymbolicSCM:
    def __init__(
        self,
        f: Dict[sp.Symbol, sp.Expr],
        pu: Dict[sp.Symbol, List],
        syn: Dict[sp.Symbol, sp.Symbol] = {},
        precision: int = 4,
    ):
        assert all(isinstance(k, sp.Symbol) for k in f), f
        assert all(isinstance(k, sp.Symbol) for k in pu), pu
        assert all(
            (
                isinstance(v, list)
                and math.isclose(sum(v), 1)
                and all(0 <= v[i] <= 1 for i in range(len(v)))
                and len(v) > 0
            )
            or (isinstance(v, float) and 0 <= v <= 1)
            for v in pu.values()
        ), pu
        assert all(isinstance(k, sp.Symbol) for k in syn), syn
        assert all(isinstance(syn[k], sp.Symbol) for k in syn), syn

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

        self.syn = dict(syn)
        self.syn.update({k: k for k in self.v})

        # display precision
        self.precision = precision

        self._counterfactuals = {k: self for k in self.v}

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

    def sample(self, n=1):
        pt = self.get_probability_table()
        return pt.sample(n=n, weights="probability", replace=True)

    def query(self, x, given={}, latex=False):
        assert all(k in self.syn for k in x), x
        assert all(k in self.syn for k in given), given

        # could be relaxed
        assert set(x).isdisjoint(given), (x, given)

        if latex:
            x_latex = ",".join(f"{k} = {v}" for k, v in x.items())
            given_latex = ",".join(f"{k} = {v}" for k, v in given.items())
            if given_latex:
                given_latex = "|" + given_latex
            query_latex = f"P({x_latex + given_latex})"
            val = f"%.{self.precision}g" % self.query(x, given)
            return Latex(f"${query_latex} \\approx {val}$")

        if given:
            return self.query({**x, **given}) / self.query(given)

        x = {self.syn[k]: v for k, v in x.items()}

        pt = self.get_probability_table()
        query = " and ".join(f"`{str(k)}` == {str(x[k])}" for k in x)
        return pt.query(query).probability.sum()

    def do(self, x):
        assert all(k in self.v for k in x), x
        subscript = ",".join(f"{k}={x[k]}" for k in x)
        vs = {k: sp.Symbol(f"{{{k}}}_{{{subscript}}}") for k in self.v}
        return SymbolicSCM(
            f={
                vs[k]: (sp.sympify(x[k]) if k in x else v).subs(vs)
                for k, v in self.f.items()
            },
            pu=self.pu,
            syn={**self.syn, **vs},
        )

    def _repr_mimebundle_(self, **kwargs):
        v = ",".join(map(str, self.v))
        u = ",".join(map(str, self.u))
        f = "\\\\".join(f"{k} &= {sp.latex(v)}" for k, v in self.f.items())
        pu = "\\\\".join(
            (
                (
                    f"{k} &\\sim \mathrm{{Categorical}}(["
                    f"{','.join(f'%.{self.precision}g' % val for val in v)}])"
                )
                if self.pu_domains[k][0] is not False
                else f"{k} &\\sim \mathrm{{Bern}}({f'%.{self.precision}g' % v[1]})"
            )
            for k, v in self.pu.items()
        )
        return {
            "text/plain": f"SCM({self.v}, {self.u})",
            "text/latex": (
                "$\\begin{cases}"
                f"\mathbf V &= \\{{{v}\\}} \\\\"
                f"\mathbf U &= \\{{{u}\\}} \\\\"
                f"F &= \\begin{{cases}}"
                f"{f}"
                "\\end{cases} \\\\"
                f"P(\mathbf U) &= \\begin{{cases}}"
                f"{pu}"
                "\\end{cases}"
                "\\end{cases}$"
            ),
        }


# class P:
#     def __init__(self, v, given={}, do={}):
#         self.v = v
#         self.given = given
#         self.do = do

#     def _repr_mimebundle_(self, **kwargs):
#         v = ', '.join(f"{k} = {v}" for k, v in self.v.items())
#         given = ', '.join(f"{k} = {v}" for k, v in self.given.items())
#         do = ', '.join(f"{k} = {v}" for k, v in self.do.items())
#         return {
#             "text/plain": f"P({v} | {given}, do({do}))",
#             "text/latex": f"$P({v} | {given}, do({do}))$",
#         }
