





from typing import Dict, List, Set, Union

import sympy as sp


def format_set(symbols:Union[Dict[sp.Symbol,int],Set[sp.Symbol]],add_brackets=False) -> str:
    """
    Given a set of sympy symbols, returns a LaTeX formatted string representing the set.
    If the set is empty, returns an empty string.
    """
    if symbols is None or len(symbols) < 1:
        return ''
    
    if isinstance(symbols, dict):
        # If the input is a dictionary, extract the keys.
        symbols_latex = ', '.join(f'{sp.latex(sym)} = {val}' for sym,val in symbols.items())
    else:
        # If the input is a set, convert each symbol to its LaTeX representation.
        symbols_latex = ', '.join({sp.latex(sym) for sym in symbols})
    
    if add_brackets:
        # Add brackets around the set.
        symbols_latex = r'\left\{' + symbols_latex + r'\right\}'
    
    return symbols_latex


def build_prob_exp(main_sets:List[str],condition_sets:List[str]=None):
    """
    Given a main set and a list of condition sets, returns a LaTeX formatted string representing the conditional.
    """
    main = ", ".join([s for s in main_sets if len(s) > 0]) if main_sets else ""
    cond = ", ".join([s for s in condition_sets if len(s) > 0]) if condition_sets else ""
    
    if len(cond) > 0:
        # Join all conditions with a comma separator.
        return r'P\left(' + main + r' \mid ' + cond + r'\right)'
    else:
        return r'P\left(' + main + r'\right)'
