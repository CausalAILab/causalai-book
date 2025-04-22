





from typing import Dict, List, Set, Union

import sympy as sp


from typing import Dict, List, Set, Union
import sympy as sp

def format_set(symbols: Union[Dict[sp.Symbol, int], Set[sp.Symbol]], add_brackets: bool = False) -> str:
    """
    Given a set of sympy symbols, returns a LaTeX formatted string representing the set.
    If the set is empty, returns an empty string.

    Parameters
    ----------
    symbols : Union[Dict[sp.Symbol, int], Set[sp.Symbol]]
        A set or dictionary of sympy symbols. If a dictionary, the values are also included in the LaTeX output.
    add_brackets : bool, optional, default=False
        A flag indicating whether to add brackets around the set.

    Returns
    -------
    str
        A LaTeX formatted string representing the set of symbols.
    """
    if symbols is None or len(symbols) < 1:
        return ''
    
    if isinstance(symbols, dict):
        # If the input is a dictionary, extract the keys and values.
        symbols_latex = ', '.join(f'{sp.latex(sym)} = {val}' for sym, val in symbols.items())
    else:
        # If the input is a set, convert each symbol to its LaTeX representation.
        symbols_latex = ', '.join({sp.latex(sym) for sym in symbols})
    
    if add_brackets:
        # Add brackets around the set.
        symbols_latex = r'\left\{' + symbols_latex + r'\right\}'
    
    return symbols_latex


def build_prob_exp(main_sets: List[str], condition_sets: List[str] = None) -> str:
    """
    Given a main set and a list of condition sets, returns a LaTeX formatted string representing the conditional.

    Parameters
    ----------
    main_sets : List[str]
        A list of LaTeX strings representing the main sets of symbols.
    condition_sets : List[str], optional, default=None
        A list of LaTeX strings representing the condition sets.

    Returns
    -------
    str
        A LaTeX formatted string representing the conditional probability expression.
    """
    main = ", ".join([s for s in main_sets if len(s) > 0]) if main_sets else ""
    cond = ", ".join([s for s in condition_sets if len(s) > 0]) if condition_sets else ""
    
    if len(cond) > 0:
        # Join all conditions with a comma separator.
        return r'P\left(' + main + r' \mid ' + cond + r'\right)'
    else:
        return r'P\left(' + main + r'\right)'

