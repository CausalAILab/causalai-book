from __future__ import annotations

import itertools
import math
from typing import Dict, List, Optional, Union

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
        """
        Initialize the structural causal model (SCM).

        Parameters:
        -----------
        f : Dict[sp.Symbol, sp.Expr]
            A dictionary mapping endogenous variables (as sympy Symbols) to
            their structural equations (as sympy Expressions).
        pu : Dict[sp.Symbol, List]
            A dictionary mapping exogenous variables (as sympy Symbols) to
            their probability distributions. Each distribution can be a list
            of probabilities summing to 1 for Categorical variables or a
            single float for Bernoulli variables.
        syn : Dict[sp.Symbol, sp.Symbol], optional
            A dictionary mapping endogenous variables to their synonymous
            variables. Defaults to an empty dictionary.
        precision : int, optional
            The precision for displaying numerical results. Defaults to 4.

        Raises:
        -------
        AssertionError
            If any of the following conditions are not met:
            - All keys in `f` are sympy Symbols.
            - All keys in `pu` are sympy Symbols.
            - All values in `pu` are either lists of probabilities summing to 1
              or single floats between 0 and 1.
            - All keys in `syn` are sympy Symbols.
            - All values in `syn` are sympy Symbols.

        Attributes:
        -----------
        v : List[sp.Symbol]
            List of endogenous variables.
        u : List[sp.Symbol]
            List of exogenous variables.
        f : Dict[sp.Symbol, sp.Expr]
            Dictionary of structural equations.
        pu_domains : Dict[sp.Symbol, List]
            Dictionary mapping exogenous variables to their domains.
        pu : Dict[sp.Symbol, List]
            Dictionary of probability distributions for exogenous variables.
        syn : Dict[sp.Symbol, sp.Symbol]
            Dictionary of synonymous variables.
        precision : int
            Precision for displaying numerical results.
        _counterfactuals : Dict[sp.Symbol, object]
            Dictionary for storing counterfactuals.
        """
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

    def _evaluate(self, u: Dict[sp.Symbol, int]) -> Dict[sp.Symbol, int]:
        """
        Evaluate the structural causal model (SCM) given the exogenous variables.

        Parameters
        ----------
        u : Dict[sp.Symbol, int]
            A dictionary where keys are sympy.Symbol instances representing
            exogenous variables and values are integers representing their
            corresponding values.
        Returns
        -------
        Dict[sp.Symbol, int]
            A dictionary where keys are sympy.Symbol instances representing
            both exogenous and endogenous variables, and values are their
            evaluated values based on the SCM.
        Raises
        ------
        AssertionError
            If the keys of `u` are not instances of sympy.Symbol.
            If the values of `u` are not integers.
            If the keys of `u` do not match the set of exogenous variables `self.pu`.
        """

        assert {isinstance(k, sp.Symbol) for k in u}, u
        assert {isinstance(v, int) for v in u.values()}, u
        assert set(u) == set(self.pu), (u, self.pu)

        v = dict(u)
        for k in self.f:
            v[k] = self.f[k].subs(v)
        return v

    def get_probability_table(
        self, symbols: Optional[List[sp.Symbol]] = None, u: bool = False
    ) -> pd.DataFrame:
        """
        Generate a probability table for the given symbols.
        Parameters
        ----------
        symbols : list, optional
            A list of symbols to include in the probability table. If None, the symbols
            will be determined based on the value of `u`. If `u` is True, the symbols
            will include both `self.u` and `self.v`. Otherwise, only `self.v` will be included.
        u : bool, default=False
            A flag indicating whether to include `self.u` symbols in the probability table.
        Returns
        -------
        pd.DataFrame
            A pandas DataFrame containing the probability table. The DataFrame will have
            columns corresponding to the specified symbols and a 'probability' column
            containing the computed probabilities.
        Notes
        -----
        The method evaluates the probability of each combination of settings in `self.pu_domains`
        and computes the probability using the values in `self.pu`.
        """

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

    def sample(self, n: int = 1) -> pd.DataFrame:
        """
        Generate a sample from the probability table.
        Parameters
        ----------
        n : int, default=1
            The number of samples to generate.
        Returns
        -------
        pd.DataFrame
            A DataFrame containing the sampled data.
        """

        pt = self.get_probability_table()
        return pt.sample(n=n, weights="probability", replace=True)

    def query(
        self,
        x: Dict[sp.Symbol, int],
        given: Dict[sp.Symbol, int] = {},
        latex: bool = False,
    ) -> Union[float, Latex]:
        """
        Query the probability of an event given some conditions.

        Parameters
        ----------
        x : Dict[sp.Symbol, int]
            A dictionary where keys are sympy.Symbol instances representing
            variables of interest and values are their corresponding values.
        given : Dict[sp.Symbol, int], optional
            A dictionary where keys are sympy.Symbol instances representing
            conditioning variables and values are their corresponding values.
            Defaults to an empty dictionary.
        latex : bool, optional
            A flag indicating whether to return the result as a LaTeX object.
            Defaults to False.

        Returns
        -------
        Union[float, Latex]
            The probability of the event specified by `x` given the conditions
            specified by `given`. If `latex` is True, returns a LaTeX object
            representing the probability.

        Raises
        ------
        AssertionError
            If any of the following conditions are not met:
            - All keys in `x` are in `self.syn`.
            - All keys in `given` are in `self.syn`.
            - The keys in `x` and `given` are disjoint.
        """
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

    def do(self, x: Dict[sp.Symbol, int]) -> SymbolicSCM:
        """
        Perform the do-operation on the structural causal model (SCM).
        The do-operation simulates an intervention where the values of certain variables
        are fixed to specific values, effectively removing the influence of their
        parent variables in the causal graph.
        Parameters
        ----------
        x : Dict[sp.Symbol, int]
            A dictionary where keys are the variables to intervene on, and values are
            the fixed values for these variables.
        Returns
        -------
        SymbolicSCM
            A new SymbolicSCM instance representing the modified SCM after the intervention.
        Raises
        ------
        AssertionError
            If any of the keys in `x` are not present in the set of variables `self.v`.
        """

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


# class P(sp.Expr):
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
