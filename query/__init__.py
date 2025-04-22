from typing import Dict, Optional, Set, Union
from sympy import Symbol, Expr
import sympy as sp

from IPython.display import Latex

from global_utils.latex_utils import format_set, build_prob_exp



# TODO: Find way to return Latex-rich objects in other package methods
# that contain .subs() and .atoms() and other methods for accessing Pr() instances
# Issue: Many objects returned are not context rich enough to be evaluated

from typing import Dict, Set, Union, Optional
from sympy import Expr, Symbol

class Pr(Symbol):
    """
    Class representing a probabilistic event with optional conditioning and intervention.

    Attributes
    ----------
    _event_obj : Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]
        The event object, which can be a dictionary or a set of symbols.
    _condition_obj : Optional[Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]]
        The conditioning object (optional).
    _do_obj : Optional[Dict[Symbol, Union[int, Symbol]]]
        The intervention (optional).

    Methods
    -------
    __new__(cls, event, given=None, do=None) -> Expr
        Creates a new instance of the Pr class, representing a probabilistic event
        with optional conditioning and intervention.
    _latex(self, printer=None) -> str
        Generates the LaTeX representation of the probabilistic expression.
    __str__(self) -> str
        Returns a string representation of the LaTeX expression.
    __repr__(self) -> str
        Returns a string representation of the LaTeX expression for debugging.
    _repr_latex_(self) -> str
        Returns a LaTeX representation for Jupyter/IPython display.
    get_event(self) -> Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]
        Returns the event object.
    get_condition(self) -> Optional[Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]]
        Returns the condition object.
    get_action(self) -> Optional[Dict[Symbol, Union[int, Symbol]]]
        Returns the do (intervention) object.
    """
    
    def __new__(cls, 
                event: Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]], 
                given: Optional[Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]] = None,
                do: Optional[Dict[Symbol, Union[int, Symbol]]] = None) -> Expr:
        """
        Creates a new instance of the Pr class, representing a probabilistic event
        with optional conditioning and intervention.
        
        Parameters
        ----------
        event : Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]
            The event object, which can be a dictionary or a set of symbols.
        given : Optional[Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]], optional
            The condition object (default is None).
        do : Optional[Dict[Symbol, Union[int, Symbol]]], optional
            The intervention object (default is None).
        
        Returns
        -------
        Expr
            A symbolic expression representing the probabilistic event.
        """
        if isinstance(event, dict):
            ev_name = ",".join(f"{k.name}={v}" for k, v in event.items())
        else:
            ev_name = ",".join(s.name for s in event)
        
        if given:
            if isinstance(given, dict):
                cond_name = ",".join(f"{k.name}={v}" for k, v in given.items())
            else:
                cond_name = ",".join(s.name for s in given)
            name = f"P({ev_name}|{cond_name})"
        else:
            name = f"P({ev_name})"
        
        if do:
            if isinstance(do, dict):
                do_name = ",".join(f"{k.name}={v}" for k, v in do.items())
            else:
                do_name = ",".join(s.name for s in do)
            name = f"P({ev_name}|do({do_name}))"
        else:
            name = f"P({ev_name})"
        
        prob = super().__new__(cls, name)
        prob._event_obj = event
        prob._condition_obj = given
        prob._do_obj = do
        
        return prob

    def _latex(self, printer=None) -> str:
        """
        Generates the LaTeX representation of the probabilistic expression.
        
        Parameters
        ----------
        printer : optional
            A printer object (default is None).
        
        Returns
        -------
        str
            A LaTeX string representing the probabilistic event.
        """
        events = format_set(self._event_obj, add_brackets=False)
        conditions = format_set(self._condition_obj, add_brackets=False)
        dos = format_set(self._do_obj, add_brackets=False)
        
        return build_prob_exp([events], [f'do({dos})' if dos != '' else '', conditions])

    def __str__(self) -> str:
        """
        Returns a string representation of the LaTeX expression.
        
        Returns
        -------
        str
            The LaTeX string representation of the probabilistic event.
        """
        return self._latex()

    def __repr__(self) -> str:
        """
        Returns a string representation of the LaTeX expression for debugging.
        
        Returns
        -------
        str
            The LaTeX string representation of the probabilistic event.
        """
        return self._latex()

    def _repr_latex_(self) -> str:
        """
        Returns a LaTeX representation for Jupyter/IPython display.
        
        Returns
        -------
        str
            The LaTeX string representation of the probabilistic event for display.
        """
        return f"${self._latex()}$"

    def get_event(self) -> Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]:
        """
        Returns the event object.
        
        Returns
        -------
        Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]
            The event object associated with the probabilistic event.
        """
        return self._event_obj

    def get_condition(self) -> Optional[Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]]:
        """
        Returns the condition object.
        
        Returns
        -------
        Optional[Union[Dict[Symbol, Union[int, Symbol]], Set[Symbol]]]
            The condition object, if provided.
        """
        return self._condition_obj

    def get_action(self) -> Optional[Dict[Symbol, Union[int, Symbol]]]:
        """
        Returns the intervention (do) object.
        
        Returns
        -------
        Optional[Dict[Symbol, Union[int, Symbol]]]
            The intervention object, if provided.
        """
        return self._do_obj

        
    
    
    
        
    