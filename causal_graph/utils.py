from abc import ABC, abstractmethod

import sympy as sp

import networkx as nx





def powerset(s):
    """
    Generate the powerset of a set.
    """
    s = list(s)
    x = len(s)
    for i in range(1 << x):
        yield {s[j] for j in range(x) if (i & (1 << j))}
        
        

        

        