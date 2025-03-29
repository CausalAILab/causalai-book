from abc import ABC, abstractmethod

import sympy as sp


import networkx as nx



class Adjustments(ABC):

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



    def is_backdoor_adjustment(self, X:sp.Symbol, Y:sp.Symbol, given:sp.Symbol):
        """
        Check if X is a backdoor adjustment for Y given the variables
        """

    def find_backdoor_adjustment(self, X:sp.Symbol, Y:sp.Symbol):
        """
        Find a backdoor adjustment set for X -> Y
        """
        
    def is_frontdoor_adjustment(self, X:sp.Symbol, Y:sp.Symbol, given:sp.Symbol):
        """
        Check if X is a frontdoor adjustment for Y given the variables
        """

    def find_frontdoor_adjustment(self, X:sp.Symbol, Y:sp.Symbol):
        """
        Find a frontdoor adjustment set for X -> Y
        """

    def find_all_backdoor_adjustments(self, X:sp.Symbol, Y:sp.Symbol):
        """
        Find all backdoor adjustment sets for X -> Y
        """

    def find_all_frontdoor_adjustments(self, X:sp.Symbol, Y:sp.Symbol):
        """
        Find all frontdoor adjustment sets for X -> Y
        """