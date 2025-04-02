from abc import ABC, abstractmethod

import sympy as sp





def powerset(self, s):
    """
    Generate the powerset of a set
    """
    x = len(s)
    for i in range(1 << x):
        yield [s[j] for j in range(x) if (i & (1 << j))]