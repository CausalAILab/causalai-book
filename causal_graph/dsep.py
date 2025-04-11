from abc import ABC, abstractmethod
from typing import List, Set, Optional, Union

import sympy as sp


import networkx as nx

import causal_graph.utils as utils
from symbol_container import SymbolContainer



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
    def combined_graph(self):
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

    def is_d_separator(
        self,
        x: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        y: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        given: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]] = None
    ) -> bool:
        """
        Check if set X is d-separated from set Y given a set of variables.
        
        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            First variable or set/list of variables for the d-separation check.
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Second variable or set/list of variables for the d-separation check.
        given : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            A variable or set/list of variables to condition on; defaults to an empty set.
        
        Returns
        -------
        bool
            True if every pair (x_val, y_val) from X and Y is d-separated given the set, False otherwise.
        """
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list, SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list, SymbolContainer)) else {y})}
        if given is None:
            giv = set()
        else:
            giv = {self.syn.get(g, g) for g in (given if isinstance(given, (set, list, SymbolContainer)) else {given})}
            
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return False
            
        if x_set & y_set:
            return False
        
        if x_set & giv or y_set & giv:
            return True
        
        for x_val in x_set:
            for y_val in y_set:
                if not nx.is_d_separator(self.combined_graph, x_val, y_val, giv):
                    return False
        return True

    def is_minimal_d_separator(
        self,
        x: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        y: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        given: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]] = None
    ) -> bool:
        """
        Check if set X is minimally d-separated from set Y given a set of variables.
        
        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            First variable or set/list of variables for the d-separation check.
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Second variable or set/list of variables for the d-separation check.
        given : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            A variable or set/list of variables to condition on; defaults to an empty set.
        
        Returns
        -------
        bool
            True if every pair (x_val, y_val) from X and Y is minimally d-separated given the set, False otherwise.
        """
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list, SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list, SymbolContainer)) else {y})}
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return False
        
        if given is None:
            giv = set()
        else:
            giv = {self.syn.get(g, g) for g in (given if isinstance(given, (set, list, SymbolContainer)) else {given})}
        if x_set & y_set:
            return False
        for x_val in x_set:
            for y_val in y_set:
                if x_val in giv or y_val in giv:
                    continue
                if not nx.is_minimal_d_separator(self.de_graph, x_val, y_val, giv):
                    return False
        return True

    def find_minimal_d_separator(
        self,
        x: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        y: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        included: Set[sp.Symbol] = None,
        restricted: Set[sp.Symbol] = None
    ) -> Union[None, SymbolContainer]:
        """
        Find a minimal set of variables that d-separates set X from set Y.
        
        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            The first variable or set/list of variables in the d-separation query.
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            The second variable or set/list of variables in the d-separation query.
        included : Set[sp.Symbol], optional
            A set of variables forced to be included in the separator, by default None.
        restricted : Set[sp.Symbol], optional
            Restricted node or set of nodes to consider.
            Only these nodes can be in the found separating set, default is None meaning all nodes.
        
        Returns
        -------
        Union[None, Set]
            The minimal set of variables that d-separates X and Y if one exists; otherwise, None.
        """
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list, SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list, SymbolContainer)) else {y})}
        included_set = {self.syn.get(i, i) for i in (included if isinstance(included, (set, list, SymbolContainer)) else {included})}if included else set()
        restricted_set = {self.syn.get(r, r) for r in (restricted if isinstance(restricted, (set, list, SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        included_set &= restricted_set
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
        
        if x_set & y_set:
            return None
        
        all_seps = {}
        
        for x_val in x_set:
            for y_val in y_set:
                seps = set(self.find_all_d_separators(x_val, y_val,included=included_set, restricted=restricted_set))
                
                if not seps:
                    continue
                
                all_seps = all_seps & seps if len(all_seps) > 1 else seps
                
        return SymbolContainer(min(all_seps, key=len),self.syn)

    def find_all_d_separators(
        self,
        x: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        y: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        included: Set[sp.Symbol] = None,
        restricted: Set[sp.Symbol] = None
    ) -> Union[None, List[SymbolContainer]]:
        """
        Find all sets of variables that d-separate set X from set Y.
        
        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            The first variable or set/list of variables in the d-separation query.
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            The second variable or set/list of variables in the d-separation query.
        included : Set[sp.Symbol], optional
            A set of variables forced to be included in the separator, by default None.
        restricted : Set[sp.Symbol], optional
            Restricted node or set of nodes to consider.
            Only these nodes can be in the found separating set, default is None meaning all nodes.
        
        Returns
        -------
        Union[None, List[SymbolContainer]]
            A list of SymbolContainer, where each set is a group of variables that d-separates X and Y.
            If X and Y share any common element, returns None.
        """
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list, SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list, SymbolContainer)) else {y})}
        
        included_set = {self.syn.get(i, i) for i in (included if isinstance(included, (set, list, SymbolContainer)) else {included})}if included else set()
        restricted_set = {self.syn.get(r, r) for r in (restricted if isinstance(restricted, (set, list, SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        included_set &= restricted_set
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
        
        if x_set & y_set:
            return None
        
        candidate_vars = set(self.v) - x_set - y_set - (x_set | y_set)
        all_seps = []
        for candidate in utils.powerset(candidate_vars):
            if (candidate & included_set) != included_set:
                continue
            if candidate & restricted_set != candidate:
                continue
            
            if all(nx.is_d_separator(self.combined_graph, x_val, y_val, candidate)
                if (x_val not in candidate and y_val not in candidate) else True
                for x_val in x_set for y_val in y_set):
                all_seps.append(SymbolContainer(candidate))
                
        return all_seps
    
    def find_all_proper_causal_paths(self,x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]], full_path:bool=True) -> List[SymbolContainer]:
        """
        Find all proper causal paths between X and Y.
        
        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            The first variable or set/list of variables in the d-separation query.
        y : Union[sp.Symbol, Set[sp.Symbol]]
            The second variable or set/list of variables in the d-separation query.
        
        Returns
        -------
        List[SymbolContainer]
            A List of SymbolContainers, where each list represents a proper causal path from X to Y.
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list, SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list, SymbolContainer)) else {y})}
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
        
        if x_set & y_set:
            return None
        
        all_paths = []
        
        for x_val in x_set:
            for y_val in y_set:
                valid_paths = []
                paths = nx.all_simple_paths(self.de_graph, source=x_val, target=y_val)
                for path in paths:
                    for step in path[1:-1]:
                        if step in x_set or step in y_set:
                            break
                    else:
                        valid_paths.append(SymbolContainer(path,self.syn))
                        
                if full_path:
                    all_paths.extend(valid_paths)
                else:
                    all_paths.extend([SymbolContainer(path[0:2],self.syn) for path in valid_paths])
                
        return len(all_paths) > 0 and all_paths or None





