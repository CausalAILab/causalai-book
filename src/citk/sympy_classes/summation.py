from sympy import Symbol, oo, Expr, sympify, Tuple, S


# TODO: Build summation wrapper class for Pr expressions



class Summation(Expr):
    """
    Represents a summation expression.

    Parameters
    ----------
    expr : Expr
        The expression to be summed.
    limits : list of tuples, optional
    """


    def __new__(cls, expr, *limits):
        
        expr = sympify(expr)
        processed_limits = []
        for lim in limits:
            if isinstance(lim, Tuple):          # already a SymPy Tuple -> keep
                processed_limits.append(lim)
            elif isinstance(lim, tuple):
                # (sym, dom)  or  (sym,)  or  (sym, None)
                sym  = sympify(lim[0])
                dom  = sympify(lim[1]) if len(lim) > 1 else S.UniversalSet
                processed_limits.append(Tuple(sym, dom))
            else:                               # plain Symbol / Expr -> no domain
                processed_limits.append(Tuple(sympify(lim), S.UniversalSet))
            
        
        return super().__new__(cls, expr,*processed_limits)
    
    
    @property
    def expr(self):
        """
        Returns the expression to be summed.
        """
        return self.args[0]
    @property
    def symbols(self):
        """
        Returns the symbols over which the summation is performed.
        """
        return [limit[0] for limit in self.args[1:]]
    
    @property
    def domains(self):
        """
        Returns the domain of the summation.
        """
        return {limit[0]:limit[1] for limit in self.args[1:]}
    
    
    def _latex(self, printer=None, *args):
        """
        Returns the LaTeX representation of the summation expression.
        """
        return r"\sum_{" + ",".join([f"{str(k)}" for k in self.symbols]) + "}{" + str(self.expr) + r"}"
    
    
    def _sympy_str(self, printer=None, *args):
        return self._latex(printer, *args)
    
    
    def __str__(self):
        """
        Returns the string representation of the summation expression.
        """
        return self._latex()
    
    def __repr__(self):
        """
        Returns the string representation of the summation expression.
        """
        return self._latex()
    
    def _repr_latex_(self):
        """
        Returns the LaTeX representation of the summation expression.
        """
        return f"${self._latex()}$"
