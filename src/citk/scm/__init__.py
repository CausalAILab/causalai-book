from __future__ import annotations

import itertools
import math

from typing import Dict, List, Optional, Union

import pandas as pd
import sympy as sp
from IPython.display import Latex

from src.sympy_classes.pr import Pr
from src.return_classes import SymbolContainer

from src import CausalGraph

from src.sympy_classes.summation import Summation
from src.sympy_classes.variable import Variable



class SymbolicSCM:


    def __init__(
        self,
        f: Dict[Variable, sp.Expr],
        pu: Dict[Variable, List],
        precision: int = 4,
    ):
        """
        Initialize the structural causal model (SCM).

        Parameters:
        -----------
        f : Dict[Variable, sp.Expr]
            A dictionary mapping endogenous variables (as sympy Symbols) to
            their structural equations (as sympy Expressions).
        pu : Dict[Variable, List]
            A dictionary mapping exogenous variables (as sympy Symbols) to
            their probability distributions. Each distribution can be a list
            of probabilities summing to 1 for Categorical variables or a
            single float for Bernoulli variables.
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
        v : List[Variable]
            List of endogenous variables.
        u : List[Variable]
            List of exogenous variables.
        f : Dict[Variable, sp.Expr]
            Dictionary of structural equations. Must be loaded sequentially by dependency.
        pu_domains : Dict[Variable, List]
            Dictionary mapping exogenous variables to their domains.
        pu : Dict[Variable, List]
            Dictionary of probability distributions for exogenous variables.
        syn : Dict[Variable, Variable]
            A dictionary mapping endogenous variables to their affected variants. Defaults to an empty dictionary.
        precision : int
            Precision for displaying numerical results.
        _counterfactuals : Dict[Variable, object]
            Dictionary for storing a lookup to counterfactual SCMs.
        _intervention_memo : Dict[int, object]
            Memoization dictionary for storing interventions.
        _distributions : Dict[Variable, pd.DataFrame]
            Dictionary for storing calculated probability distributions.
        """
        assert all(isinstance(k, Variable) for k in f), f
        assert all(isinstance(k, Variable) for k in pu), pu
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



        self.f = {k: sp.sympify(v) for k, v in f.items()}
        
        # Potential values taken on for the endogenous variables
        # Currently limited to binary variables
        self.v_domains = {
            k: (
                [0, 1]
            )
            for k, v in f.items()
        }

        self.pu_domains = {
            k: (
                [False, True]
                if isinstance(v, float)
                else [i for i in range(len(v)) if v[i]]
            )
            for k, v in pu.items()
        }
        self.pu = {k: v if isinstance(v, list) else [1 - v, v] for k, v in pu.items()}

        self.v = SymbolContainer(list(f))
        self.u = SymbolContainer(list(pu))
        
        self.syn = {Variable(n.main): n for n in self.v}

        # display precision
        self.precision = precision
        self._intervention_memo: Dict[int, SymbolicSCM] = {}
        self._counterfactuals: Dict[Variable, SymbolicSCM] = {k: self for k in self.v}

        self._distributions: Dict[Variable, pd.DataFrame] = {}

        self.graph = CausalGraph.from_scm(self)

    def _evaluate(self, u: Dict[Variable, int]) -> Dict[Variable, int]:
        """
        Evaluate the structural causal model (SCM) given the exogenous variables.

        Parameters
        ----------
        u : Dict[Variable, int]
            A dictionary where keys are sympy.Symbol instances representing
            exogenous variables and values are integers representing their
            corresponding values.
        Returns
        -------
        Dict[Variable, int]
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

        assert {isinstance(k, Variable) for k in u}, u
        assert {isinstance(v, int) for v in u.values()}, u
        assert set(u) == set(self.pu), (u, self.pu)

        v = dict(u)
        for k in self.f:
            v[k] = self.f[k].subs(v)
        return v
    
    def _evaluate_symbolic_expression(self, expression: sp.Expr, u:Dict[Variable,int]) -> int:
        """
        Evaluate the symbolic expression through atoms deconstruction and value substitution.

        Parameters
        ----------
        expression : sp.Expr
            A sympy expression representing the symbolic expression.
        u : Dict[Variable, int]
            A dictionary of exogenous variables and their corresponding settings.
        Returns
        -------
        int
            An integer value representing the evaluated expression based on the SCM.
        """

        output = expression
        dist = None

        syms = expression.atoms(Variable)

        for s in syms:
            if self._distributions.get(s) is None:
                dist = self.get_probability_table([s], include_u=True)
            else:
                dist = self._distributions[s]

            val = int(dist.query(' & '.join(f"{k} == {v}" for k,v in u.items()))[s].values[0])

            self._distributions[s] = dist

            output = output.subs(s, val)
                

        return hash(output)
    

    def get_probability_table(
        self, symbols: Optional[List[Variable]] = None, include_u: bool = False
    ) -> pd.DataFrame:
        """
        Generate a probability table for the given symbols.
        Parameters
        ----------
        symbols : list, optional
            A list of symbols to include in the probability table. If None, the symbols
            will be determined based on the value of `u`. If `include_u` is True, the symbols
            will include both `self.u` and `self.v`. Otherwise, only `self.v` will be included.
        include_u : bool, default=False
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
        Raises
        ------
        AssertionError
            If any key is both in the set of (counterfactuals on) the endogenous variables and the set of unobserved variables.
        """
        
        _symbols = []
        
        if include_u:
            _symbols += list(self.u)

        if symbols is None:
            _symbols += list(self.v)
        else:
            _symbols += [self.syn.get(k, k) for k in symbols]
            
        
        assert all(
            (k in self._counterfactuals) != (k in self.pu) for k in _symbols
        ), _symbols

        settings = [[(k, i) for i in v] for k, v in self.pu_domains.items()]
        records = []
        for u in map(dict, itertools.product(*settings)):
            record = {}
            for scm in set(
                self._counterfactuals[k] for k in _symbols if k not in self.pu
            ):
                record.update(scm._evaluate(u))
 
            records.append(
                {
                    k:
                        hash(v) if v in [sp.false, sp.true] 
                            else 
                        int(v) if isinstance(v,(int,sp.core.numbers.Zero,sp.core.numbers.One,sp.core.numbers.Integer,float))
                            else self._evaluate_symbolic_expression(v,u)
                        for k, v in record.items()
                }
            )

            # Log-transformed multiplication of probabilities
            records[-1]["probability"] = math.exp(
                sum(math.log(self.pu[k][u[k]]) for k in self.u)
            )
                    

        return pd.DataFrame(records).groupby(list(_symbols)).probability.sum().reset_index()

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
    
    
    def query_exp(self, expr: sp.Expr, latex: bool = False) -> Union[float, Latex]:
        """
        Query the probability of an event given some conditions. Can accept both evaluable and inequality expressions. 

        Parameters
        ----------
        expr : sp.Expr
            A sympy expression consisting of Pr() objects and relevant operators.
        latex : bool, optional
            A flag indicating whether to return the result as a LaTeX object.
            Defaults to False.

        Returns
        -------
        Union[float, Latex]
            The probability of the event specified by `expr`. If `latex` is True,
            returns a LaTeX object representing the probability.

        """
        
        assert isinstance(expr,sp.Basic), "Did you mean to use query()?"
        
        result = expr

            
        for s in result.atoms(Summation):
            symbols = s.symbols
            intrinsic_domains = s.domains

            grids = [list(self.v_domains[self.syn[sym]]) if intrinsic_domains[sym] is sp.S.UniversalSet
                     else intrinsic_domains[sym] for sym in symbols]

            total = 0.0
            for vals in itertools.product(*grids):
                sub_map = dict(zip(symbols, vals))
                sub_expr = s.expr
                

                for pr in sub_expr.atoms(Pr):
                    
                    mapped_pr = pr.apply_value_map(sub_map)
                    
                    scm = self
                    if mapped_pr.get_action():
                        scm = self.do(mapped_pr.get_action())
                    sub_expr = sub_expr.subs(pr, scm.query(mapped_pr.get_event(), mapped_pr.get_condition()))

                total += float(sub_expr)
                
            result = result.xreplace({s: total})
            

        if isinstance(result, sp.Basic):
            for pr in result.atoms(Pr):
                scm = self.do(pr.get_action()) if pr.get_action() else self
                result = result.xreplace({pr: scm.query(pr.get_event(), pr.get_condition())})
                
                
        if expr.is_Relational:
            result = bool(result)
        else:
            result =  float(result)


        if not latex:
            return result
            

            
            
        pr_syms = [p for p in expr.atoms(sp.Symbol) if isinstance(p, Pr)]
        symbol_names = {p.get_id(): p._latex() for p in pr_syms}

        if expr.is_Relational:
            return Latex(
                f"$({sp.latex(expr, symbol_names=symbol_names)})"
                f" = \\text{{{result}}}$"
            )

        return Latex(
            f"${sp.latex(expr, symbol_names=symbol_names)}"
            f" \\approx {result:.{self.precision}g}$"
        )



    def query(
        self,
        x: Dict[Variable, int],
        given: Dict[Variable, int] = None,
        latex: bool = False,
    ) -> Union[float, Latex]:
        """
        Query the probability of an event given some conditions.

        Parameters
        ----------
        x : Dict[Variable, int]
            A dictionary where keys are sympy.Symbol instances representing
            variables of interest and values are their corresponding values.
        given : Dict[Variable, int], optional
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
        
        if given is None:
            given = {}
        
        assert isinstance(x,dict), "Did you mean to use query_exp()?"
        
        assert all(k in self.syn or k in self._counterfactuals for k in x), (
            x,
            self._counterfactuals,
        )

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

        x = {self.syn.get(k, k): v for k, v in x.items()}

        pt = self.get_probability_table(symbols=list(x))
        query = " and ".join(f"`{str(k)}` == {str(x[k])}" for k in x)
        return pt.query(query).probability.sum()

    def do(self, x: Dict[Variable, Union[sp.Expr, int, Variable]]) -> SymbolicSCM:
        
        """
        Perform the do-operation on the structural causal model (SCM).
        The do-operation simulates an intervention where the values of certain variables
        are fixed to specific values, effectively removing the influence of their
        parent variables in the causal graph.
        Parameters
        ----------
        x : Dict[Variable, Union[sp.Expr, int, Variable]]
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
            If any of the counterfactual values in `x` do not belong to the domain of the key.
        """

        key = hash(tuple(sorted(x.items(), key=lambda t: (str(t[0]), t[1]))))
        if key in self._intervention_memo:
            return self._intervention_memo[key]


        assert all(k in self.v for k in x), x

        assert all(isinstance(val, int) or isinstance(val, Variable) or isinstance(val, sp.Basic)
                    for k, val in x.items()), x


        vs = {k: k.update_interventions(x) for k in self.v}

        self._intervention_memo[key] = scm = SymbolicSCM(
            f={
                vs[k]: (sp.sympify(x[k]) if k in x else v).subs(vs)
                for k, v in self.f.items()
            },
            pu=self.pu,
        )

        ctfs = {k: scm for k in scm.v}
        assert set(ctfs).isdisjoint(self._counterfactuals), (
            ctfs,
            self._counterfactuals,
        )
        

        
        self._counterfactuals.update(ctfs)
        scm._counterfactuals = self._counterfactuals

        return scm

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
