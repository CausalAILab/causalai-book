from abc import ABC, abstractmethod
from typing import List, Set, Optional, Union

import sympy as sp


import networkx as nx

from .utils import powerset



class DSeparation(ABC):

    @property
    @abstractmethod
    def de_graph(self):
        pass

    @property
    @abstractmethod
    def be_graph(self):
        pass

    @property
    @abstractmethod
    def v(self):
        pass

    @property
    @abstractmethod
    def syn(self):
        pass

    @property
    @abstractmethod
    def cc(self):
        pass


    def is_d_separator(self, x: sp.Symbol, y: sp.Symbol, given: Set[sp.Symbol] = set()) -> bool:
        """
        Check if X is d-separated from Y given a set of variables.

        Parameters
        ----------
        x : sp.Symbol
            First variable for the d-separation check.
        y : sp.Symbol
            Second variable for the d-separation check.
        given : Set[sp.Symbol], optional
            The set of endogenous variables to condition on, by default set().

        Returns
        -------
        bool
            A Boolean representing whether X is d-separated from Y given the set of variables.
        """

        X = self.syn.get(x, x)
        Y = self.syn.get(y, y)

        giv = {self.syn.get(g, g) for g in given}

        if X == Y:
            return False

        if X in giv or Y in giv:
            return True

        for comp in self.cc:
            if X in comp and Y in comp:
                return False

        return nx.is_d_separator(self.de_graph, X, Y, giv)


    def is_minimal_d_separator(self, x: sp.Symbol, y: sp.Symbol, given: Set[sp.Symbol] = set()) -> bool:
        """
        Check if X is minimally d-separated from Y given a set of variables.

        Parameters
        ----------
        x : sp.Symbol
            First variable for the d-separation check.
        y : sp.Symbol
            Second variable for the d-separation check.
        given : Set[sp.Symbol], optional
            The set of variables to condition on, by default set().

        Returns
        -------
        bool
            True if X is minimally d-separated from Y given the set of variables, False otherwise.
        """

        X = self.syn.get(x, x)
        Y = self.syn.get(y, y)

        giv = {self.syn.get(g, g) for g in given}

        if X == Y:
            return False

        if X in giv or Y in giv:
            return True

        for comp in self.cc:
            if X in comp and Y in comp:
                return False

        return nx.is_minimal_d_separator(self.de_graph, X, Y, giv)


    def find_minimal_d_separator(self, x: sp.Symbol, y: sp.Symbol, included: Set[sp.Symbol] = None, restricted: Set[sp.Symbol] = None) -> Union[None, Set]:
        """
        Find a minimal set of variables that d-separates X from Y.

        Parameters
        ----------
        x : sp.Symbol
            The first variable in the d-separation query.
        y : sp.Symbol
            The second variable in the d-separation query.
        included : Set[sp.Symbol], optional
            A set of variables that are forced to be included in the separator, by default None.
        restricted : Set[sp.Symbol], optional
            A set of variables that are excluded from the separator, by default None.

        Returns
        -------
        Union[None, Set]
            The minimal set of variables that d-separates X and Y if one exists; otherwise, None.
        """

        X = self.syn.get(x, x)
        Y = self.syn.get(y, y)

        if X == Y:
            return None

        for comp in self.cc:
            if X in comp and Y in comp:
                return None

        return nx.find_minimal_d_separator(self.de_graph, X, Y, included, restricted)


    def find_all_d_separators(self, x: sp.Symbol, y: sp.Symbol) -> Union[None, List[Set]]:
        """
        Find all sets of variables that d-separate X from Y.

        Parameters
        ----------
        x : sp.Symbol
            The first variable in the d-separation query.
        y : sp.Symbol
            The second variable in the d-separation query.

        Returns
        -------
        Union[None, List[Set]]
            A list of sets, where each set is a group of variables that d-separates X and Y.
            If X and Y are identical or belong to the same connected component, returns [None].
        """

        X = self.syn.get(x, x)
        Y = self.syn.get(y, y)

        if X == Y:
            return [None]

        for comp in self.cc:
            if X in comp and Y in comp:
                return [None]

        v_less_xy = set(self.v) - {X, Y}

        return [s for s in powerset(v_less_xy) if nx.is_d_separator(self.de_graph, X, Y, s)]








        

        



