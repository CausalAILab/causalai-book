

import sympy as sp
import networkx as nx
from abc import ABC, abstractmethod

from typing import List, Set, Union

from symbol_container import SymbolContainer


class Accessors(ABC):
    
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
    
    def get_parents(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False
    ):
        """
        Return a SymbolContainer with the union of the parents of the given node(s).
        
        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or collection of nodes whose parents are to be retrieved.
        include_self : bool, optional
            If True, include the given node(s) in the result, by default False.
        
        Returns
        -------
        SymbolContainer
            A SymbolContainer containing the union of the parents of the given node(s).
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = {p for n in nodes for p in self.de_graph.predecessors(n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result, self.syn)

    def get_children(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False
    ):
        """
        Return a SymbolContainer with the union of the children of the given node(s).
        
        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or collection of nodes whose children are to be retrieved.
        include_self : bool, optional
            If True, include the given node(s) in the result, by default False.
        
        Returns
        -------
        SymbolContainer
            A SymbolContainer containing the union of the children of the given node(s).
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = {c for n in nodes for c in self.de_graph.successors(n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result, self.syn)

    def get_ancestors(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False
    ):
        """
        Return a SymbolContainer with the union of the ancestors of the given node(s).
        
        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or collection of nodes whose ancestors are to be retrieved.
        include_self : bool, optional
            If True, include the given node(s) in the result, by default False.
        
        Returns
        -------
        SymbolContainer
            A SymbolContainer containing the union of the ancestors of the given node(s).
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = {a for n in nodes for a in nx.ancestors(self.de_graph, n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result, self.syn)

    def get_descendants(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False
    ):
        """
        Return a SymbolContainer with the union of the descendants of the given node(s).
        
        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or collection of nodes whose descendants are to be retrieved.
        include_self : bool, optional
            If True, include the given node(s) in the result, by default False.
        
        Returns
        -------
        SymbolContainer
            A SymbolContainer containing the union of the descendants of the given node(s).
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = {d for n in nodes for d in nx.descendants(self.de_graph, n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result, self.syn)

    def get_neighbors(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False
    ):
        """
        Return a SymbolContainer with the union of the neighbors of the given node(s).
        
        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or collection of nodes whose neighbors are to be retrieved.
        include_self : bool, optional
            If True, include the given node(s) in the result, by default False.
        
        Returns
        -------
        SymbolContainer
            A SymbolContainer containing the union of the neighbors of the given node(s).
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = {nbr for n in nodes for nbr in self.be_graph.neighbors(n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result, self.syn)

    def get_connected_components(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
    ):
        """
        Return a SymbolContainer with the union of the connected components containing the given node(s).
        
        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or collection of nodes whose connected component(s) are to be retrieved.
        include_self : bool, optional
            If True, include the given node(s) in the result, by default False.
        
        Returns
        -------
        SymbolContainer
            A list of connected components as SymbolContainers.
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = []
        for comp in self.cc:
            if comp & nodes:
                result.append(SymbolContainer(comp,self.syn))
        return result
