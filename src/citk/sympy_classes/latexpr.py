




class Latexpr(sp.Expr):
    """
    A class to represent a LaTeX expression.
    
    Parameters
    ----------
    expr : str
        The LaTeX expression as a string.
    
    Attributes
    ----------
    expr : str
        The LaTeX expression as a string.
    
    Methods
    -------
    _latex() -> str
        Returns the LaTeX representation of the expression.
    
    _repr_latex_() -> str
        Returns the LaTeX representation for Jupyter/IPython display.
    """
    
    def __new__(cls, expr: str):
        obj = super().__new__(cls, expr)
        obj.expr = expr
        return obj
    
    
    def _latex(self, printer=None) -> str:
        """
        Returns the LaTeX representation of the expression.
        
        Parameters
        ----------
        printer : optional
            The printer to use for rendering the LaTeX expression.
        
        Returns
        -------
        str
            The LaTeX representation of the expression.
        """
        return self.expr
    
    def _repr_latex_(self) -> str:
        """
        Returns the LaTeX representation for Jupyter/IPython display.
        
        Returns
        -------
        str
            The LaTeX representation of the expression.
        """
        return r"$" + self._latex() + r"$"