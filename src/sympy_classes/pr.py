from typing import Dict, Optional, Set, Union
import uuid


from src.return_classes.symbol_container import SymbolContainer
from src.sympy_classes.variable import Variable
from sympy import Symbol, Expr
import sympy as sp

from IPython.display import Latex

from src.global_utils import format_set, build_prob_exp




# TODO: Find way to return Latex-rich objects in other package methods
# that contain .subs() and .atoms() and other methods for accessing Pr() instances
# Issue: Many objects returned are not context rich enough to be evaluated


class Pr(Symbol):
    """
    Class representing a probabilistic event with optional conditioning and intervention.

    Attributes
    ----------
    _event_obj : Union[Dict[Variable, Union[int, Variable]], Set[Variable]]
        The event object, which can be a dictionary or a set of symbols.
    _condition_obj : Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]]
        The conditioning object (optional).
    _do_obj : Optional[Dict[Variable, Union[int, Variable]]]
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
    get_event(self) -> Union[Dict[Variable, Union[int, Variable]], Set[Variable]]
        Returns the event object.
    get_condition(self) -> Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]]
        Returns the condition object.
    get_action(self) -> Optional[Dict[Variable, Union[int, Variable]]]
        Returns the do (intervention) object.
    """
    
    def __new__(cls, 
                event: Union[Dict[Variable, Union[int, Variable]], Set[Variable]], 
                given: Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]] = None,
                do: Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]] = None) -> Expr:
        """
        Creates a new instance of the Pr class, representing a probabilistic event
        with optional conditioning and intervention.
        
        Parameters
        ----------
        event : Union[Dict[Variable, Union[int, Variable]], Set[Variable]]
            The event object, which can be a dictionary or a set of symbols.
        given : Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]], optional
            The condition object (default is None).
        do : Optional[Dict[Variable, Union[int, Variable]]], optional
            The intervention object (default is None).
        
        Returns
        -------
        Expr
            A symbolic expression representing the probabilistic event.
        """
        
        
        _id = uuid.uuid4().hex
        
        prob = super().__new__(cls, f"Pr_{_id}")
        prob._id = f"Pr_{_id}"
        
        if isinstance(event, dict):
            event = {k:v for k,v in event.items()}
        
        if isinstance(event, (set,list)):
            event = {
                            **{k:None for k in list(event)}
                            }
            
        if isinstance(given, dict):
            given = {k:v for k,v in given.items()}
        if isinstance(given, (set,list)):
            given = {
                            **{k:None for k in list(given)}
                        }
            
        if isinstance(do, dict):
            do = {k:v for k,v in do.items()}
        if isinstance(do, (set,list)):
            do = {
                            **{k:None for k in list(do) if k.main==str(k.name)},
                            **{Variable(k.main):k for k in list(do) if k.main!=str(k.name)}
                            }
        
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
    
    def _sympystr(self, printer=None) -> str:
        """
        Returns the string representation of the probabilistic expression.
        
        Parameters
        ----------
        printer : optional
            A printer object (default is None).
        
        Returns
        -------
        str
            The string representation of the probabilistic event.
        """
        return self._latex(printer=printer)

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
    
    
    @property
    def vars(self) -> SymbolContainer:
        """
        Returns a SymbolContainer containing all variables in the event and condition objects.
        """
        
        combined = self._event_obj | self._condition_obj
        
        return SymbolContainer(list(combined.keys()))
    
    def get_id(self) -> str:
        """
        Returns the unique identifier of the probabilistic event.
        
        Returns
        -------
        str
            The unique identifier of the probabilistic event.
        """
        return self._id

    def get_event(self) -> Union[Dict[Variable, Union[int, Variable]], Set[Variable]]:
        """
        Returns the event object.
        
        Returns
        -------
        Union[Dict[Variable, Union[int, Variable]], Set[Variable]]
            The event object associated with the probabilistic event.
        """
        return self._event_obj

    def get_condition(self) -> Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]]:
        """
        Returns the condition object.
        
        Returns
        -------
        Optional[Union[Dict[Variable, Union[int, Variable]], Set[Variable]]]
            The condition object, if provided.
        """
        return self._condition_obj

    def get_action(self) -> Optional[Dict[Variable, Union[int, Variable]]]:
        """
        Returns the intervention (do) object.
        
        Returns
        -------
        Optional[Dict[Variable, Union[int, Variable]]]
            The intervention object, if provided.
        """
        return self._do_obj
    
    
    def apply_value_map(self, map:Dict[Variable, Union[int,Variable]]) -> 'Pr':
        """
        Apply a mapping of new values to old values in the event, condition, and do dictionaries.
        Produces a new instance of the Pr class with the updated values.
        
        """
        
        mapped_pr = self.__new__(self.__class__, self._event_obj, self._condition_obj, self._do_obj)
        
        for ov, nv in map.items():
            for k,v in mapped_pr._event_obj.items():
                if v == ov:
                    mapped_pr._event_obj[k] = nv
            if mapped_pr._condition_obj is not None:
                for k,v in mapped_pr._condition_obj.items():
                    if v == ov:
                        mapped_pr._condition_obj[k] = nv
            if mapped_pr._do_obj is not None:
                for k,v in mapped_pr._do_obj.items():
                    if v == ov:
                        mapped_pr._do_obj[k] = nv
                    
                    
        return mapped_pr
                                
    
    
    def apply_bayes(self, flip:Set[Variable]=None) -> sp.Expr:
        """
        Apply Bayes' theorem to the probabilistic expression.
        
        Parameters
        ----------
        flip : Set[Variable], optional
            A set of variables to flip (default is None).
        
        Returns
        -------
        sp.Expr
            The modified expression after applying Bayes' theorem.
        """
        if flip is None:
            flip = self.get_condition().copy()
        else:
            flip = {k:v for k,v in self.get_condition().items() if k in flip}
            
        assert (set(flip.keys()) & set(self.get_condition().keys())) == set(flip.keys()), \
            f"flip {flip} not in condition {self.get_condition()}"
            
        leave = [v for v in self.get_condition() if v not in flip]
        
        return (
            Pr(self.get_event() | flip, given=leave, do=self.get_action()) / Pr(flip, given=leave, do=self.get_action())
        )
        

    @staticmethod
    def apply_bayes_inverse(expr:sp.Expr) -> sp.Expr:
        
        """
        Apply Bayes' theorem to the probabilistic expression.
        
        Parameters
        ----------
        expr : sp.Expr
            The expression to which Bayes' theorem will be applied.
        
        Returns
        -------
        sp.Expr
            The modified expression after applying Bayes' theorem.
        """
        
        
        num, den = expr.as_numer_denom()
        
        assert all([isinstance(num,Pr), isinstance(den,Pr)]), \
            f"Expect Pr/Pr, got {type(num)} and {type(den)}"
        
        N_e, N_c, N_d = num.get_event(), num.get_condition(), num.get_action()
        D_e, D_c, D_d = den.get_event(), den.get_condition(), den.get_action()
        
        D_c = D_c if D_c else {}
        N_c = N_c if N_c else {}
        
        assert N_d == D_d, f"Do actions do not match: {N_d} and {D_d}"
        
        event_new = {k:v for k,v in (N_e | D_c).items() if k not in (D_e | N_c).keys()}
        condition_new = D_e | N_c | D_c
        
        
        if N_c == D_c:
            leftover = 1
        else:
            num_fac = Pr(D_c) if D_c else 1
            den_fac = Pr(N_c) if N_c else 1
            leftover = num_fac / den_fac
            
        return Pr(event_new, given=condition_new, do=N_d) * leftover
        
        
        
        
        
                
            
        

        
    
    
    
        
    