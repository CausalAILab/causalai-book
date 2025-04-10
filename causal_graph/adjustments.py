from abc import ABC, abstractmethod

import sympy as sp


import networkx as nx

from typing import List, Set, Dict, Tuple, Union

from causal_graph.dsep import DSeparation
from causal_graph.accessors import Accessors
from symbol_container import SymbolContainer

import causal_graph.utils as utils



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

    
    

    def get_proper_backdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]]):
        """
        Get the conditional backdoor graph for X -> Y given the variables
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list)) else {y})}
        
        trunc_pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=False)
        
        graph = self.__class__(self.v,
                               [edge for edge in self.de_graph.edges if SymbolContainer(edge,self.syn) not in trunc_pcp],
                               self.be_graph.edges)
        
        return graph

    def get_backdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]]):
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else {x})}

        graph = self.__class__(self.v,
                                [edge for edge in self.de_graph.edges if edge[0] not in x_set],
                                self.be_graph.edges)

        
        return graph
    
    
    
    def get_frontdoor_graph(self, X:Union[sp.Symbol, Set[sp.Symbol]]):
    
        pass
    

    def is_backdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None):
        """
        Check if X is a backdoor adjustment for Y given the variables
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list)) else {z})} if z else set()
        
        
        bd_graph = self.get_proper_backdoor_graph(x_set,y_set)
        
        do_graph = self.do_x(x_set)
        
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        for path in pcp:
            for step in path[1:]:
                w_desc = set(do_graph.get_descendants(step,include_self=True))
                if (z_set & w_desc):
                    return False

        return bd_graph.is_d_separator(x_set, y_set, z_set)
        
        
        
    def _exists_sep(self, x, y, z0, bd_graph, do_graph, pcp):
        """
        Check if there is a separation between X and Y given Z
        """
        for path in pcp:
            for step in path[1:]:
                w_desc = set(do_graph.get_descendants(step,include_self=True))
                if (z0 & w_desc):
                    return False

        return bd_graph.is_d_separator(x, y, z0)
    
    def _list_seps(self, x, y, included, restricted, bd_graph, do_graph, pcp):
        
        z0 = set(self.get_ancestors(x | y | included, include_self=True)) & restricted
        
        if self._exists_sep(x, y, z0, bd_graph, do_graph, pcp):
            if (included | restricted) == included:
                return included
            else:
                w = list(restricted - included)[-1]
                
                res1 = self._list_seps(x, y, included | {w}, restricted, bd_graph, do_graph, pcp)
                res2 = self._list_seps(x, y, included, restricted - {w}, bd_graph, do_graph, pcp)
                
                if res2 is not None:
                    return res2
                elif res1 is not None:
                    return res1
        
        return None

    def find_backdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               included:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None) -> SymbolContainer:
        """
        Find a backdoor adjustment set for X -> Y
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list)) else {y})}
        included_set = {self.syn.get(included_val, included_val) for included_val in (included if isinstance(included, (set, list)) else {included})} if included else set(self.v) - x_set - y_set
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        included_set &= restricted_set
        
        bd_graph = self.get_proper_backdoor_graph(x_set,y_set)
        do_graph = self.do_x(x_set)
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        
        return SymbolContainer(self._list_seps(x_set,y_set,included_set, restricted_set, bd_graph, do_graph, pcp),self.syn)
    
    
        
    def find_all_backdoor_adjustments(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               included:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None) -> List[SymbolContainer]:
        
        
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list)) else {y})}
        included_set = {self.syn.get(included_val, included_val) for included_val in (included if isinstance(included, (set, list)) else {included})} if included else set(self.v) - x_set - y_set
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        included_set &= restricted_set
        
        bd_graph = self.get_proper_backdoor_graph(x_set,y_set)
        do_graph = self.do_x(x_set)
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        
        return [s for s in utils.powerset(restricted_set) if ((sym in included for sym in s) and (self._exists_sep(x_set, y_set, s, bd_graph, do_graph, pcp)))]
        
        
        
        
    def is_frontdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:sp.Symbol, given:sp.Symbol):
        """
        Check if X is a frontdoor adjustment for Y given the variables
        """

    def find_frontdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:sp.Symbol):
        """
        Find a frontdoor adjustment set for X -> Y
        """

    def find_all_frontdoor_adjustments(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:sp.Symbol):
        """
        Find all frontdoor adjustment sets for X -> Y
        """