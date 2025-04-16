





from typing import Set

import sympy as sp


def format_set(symbols:Set[sp.Symbol],add_brackets=False) -> str:
    """
    Given a set of sympy symbols, returns a LaTeX formatted string representing the set.
    If the set is empty, returns an empty string.
    """
    if len(symbols) < 1:
        return ''
    # Convert each symbol to its LaTeX representation and join with commas.
    symbols_latex = ', '.join(sp.latex(sym) for sym in symbols)
    
    if add_brackets:
        # Add brackets around the set.
        symbols_latex = r'\left\{' + symbols_latex + r'\right\}'
    
    return symbols_latex


def build_conditional_set(main_set:str,*condition_sets:str):
    """
    Given a main set and a list of condition sets, returns a LaTeX formatted string representing the conditional.
    """
    main = main_set
    # Filter out any empty conditions.
    conditions = [cond for cond in condition_sets if cond]
    
    if conditions:
        # Join all conditions with a comma separator.
        cond_str = ', '.join(conditions)
        return r'P\left(' + main + r' \mid ' + cond_str + r'\right)'
    else:
        return r'P\left(' + main + r'\right)'
    
    
def build_joint_set(*joint_sets:str):
    """
    Given a list of joint sets, returns a LaTeX formatted string representing the joint distribution.
    """
    # Filter out any empty sets.
    joint_sets = [joint for joint in joint_sets if joint]
    
    if joint_sets:
        # Join all sets with a comma separator.
        joint_str = ', '.join(joint_sets)
        return r'P\left(' + joint_str + r'\right)'
    else:
        return ''
