from typing import Dict, Optional, Set, Union
from sympy import Symbol, Expr
import sympy as sp

from IPython.display import Latex

from global_utils.latex_utils import format_set, build_prob_exp



# TODO: Find way to return Latex-rich objects in other package methods
# that contain .subs() and .atoms() and other methods for accessing Pr() instances
# Issue: Many objects returned are not context rich enough to be evaluated

# TODO: Add do class that will initiate a do() call in query_exp

class Pr(Symbol):
    
    def __new__(cls, event:Union[Dict[Symbol,Union[int,Symbol]],Set[Symbol]],
                        given:Optional[Union[Dict[Symbol,Union[int,Symbol]],Set[Symbol]]]=None,
                        do:Optional[Dict[Symbol,Union[int,Symbol]]]=None) -> Expr:
        
        if isinstance(event, dict):
            ev_name = ",".join(f"{k.name}={v}" for k,v in event.items())
        else:
            ev_name = ",".join(s.name for s in event)
        if given:
            if isinstance(given, dict):
                cond_name = ",".join(f"{k.name}={v}" for k,v in given.items())
            else:
                cond_name = ",".join(s.name for s in given)
            name = f"P({ev_name}|{cond_name})"
        else:
            name = f"P({ev_name})"
        if do:
            if isinstance(do, dict):
                do_name = ",".join(f"{k.name}={v}" for k,v in do.items())
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
                
        events = format_set(self._event_obj,add_brackets=False)
        conditions = format_set(self._condition_obj,add_brackets=False)
        dos = format_set(self._do_obj,add_brackets=False)
    
        
        return build_prob_exp([events], [f'do({dos})' if dos != '' else '',conditions])
    
    
    def __str__(self):              # str(obj)   → plain LaTeX string
        return self._latex()

    def __repr__(self):             # repr(obj)  → debugging fallback
        return self._latex()

    def _repr_latex_(self):         # Jupyter/IPython rich display
        return f"${self._latex()}$"

    
    def get_event(self) -> Union[Dict[Symbol,Union[int,Symbol]],Set[Symbol]]:
        """
        Returns the event object.
        """
        return self._event_obj
    
    def get_condition(self) -> Optional[Union[Dict[Symbol,Union[int,Symbol]],Set[Symbol]]]:
        """
        Returns the given object.
        """
        return self._condition_obj
    
    def get_action(self) -> Optional[Dict[Symbol,Union[int,Symbol]]]:
        """
        Returns the do object.
        """
        return self._do_obj
        
    
    
    
        
    