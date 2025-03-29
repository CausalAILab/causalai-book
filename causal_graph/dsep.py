from abc import ABC, abstractmethod
from typing import List

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



    def is_d_separator(self, x:sp.Symbol, y:sp.Symbol, given=set()) -> bool:
        """
        Check if X is d-separated from Y given a set of variables

        Parameters
        ----------
        x : sp.Symbol
            _description_
        y : sp.Symbol
            _description_
        given : _type_, optional
            _description_, by default set()

        Returns
        -------
        bool
            _description_
        """

        X = self.syn.get(x,x)
        Y = self.syn.get(y,y)

        giv = {self.syn.get(g,g) for g in given}

        if(X == Y):
            return False

        if(X in giv or Y in giv):
            return True
        
        for comp in self.cc:
            if(X in comp and Y in comp):
                return False
            
        
        return nx.is_d_separator(self.de_graph, X, Y, giv)
    

    def is_minimal_d_separator(self, x:sp.Symbol, y:sp.Symbol, given=set()) -> bool:
        """
        Check if X is minimally d-separated from Y given a set of variables
        """

        X = self.syn.get(x,x)
        Y = self.syn.get(y,y)

        giv = {self.syn.get(g,g) for g in given}

        if(X == Y):
            return False

        if(X in giv or Y in giv):
            return True
        
        for comp in self.cc:
            if(X in comp and Y in comp):
                return False
            
        
        return nx.is_minimal_d_separator(self.de_graph, X, Y, giv)
    
    

    def find_minimal_d_separator(self, x:sp.Symbol, y: sp.Symbol, included: Set[sp.Symbol]=None, restricted: Set[sp.Symbol]=None) -> Union[None,Set]:
        """
        Find a minimal set of variables that d-separates X from Y
        """

        X = self.syn.get(x,x)
        Y = self.syn.get(y,y)

        if(X == Y):
            return None
        
        for comp in self.cc:
            if(X in comp and Y in comp):
                return None

        return nx.find_minimal_d_separator(self.de_graph, X, Y, included, restricted)
    

    def find_all_d_separators(self, x:sp.Symbol, y: sp.Symbol) -> Union[None,List[Set]]:
        """
        Find all sets of variables that d-separates X from Y
        """

        X = self.syn.get(x,x)
        Y = self.syn.get(y,y)

        if(X == Y):
            return [None]
        
        for comp in self.cc:
            if(X in comp and Y in comp):
                return [None]

        v_less_xy = set(self.v) - {X,Y}

        return [s for s in powerset(v_less_xy) if nx.is_d_separator(self.de_graph, X, Y, s)]







        

        



