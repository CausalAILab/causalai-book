from abc import ABC, abstractmethod
from typing import List, Set, Union

from src.sympy_classes.variable import Variable
import sympy as sp
import networkx as nx


from src.return_classes import SymbolContainer




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
        Return a SymbolContainer of the parents of the given node(s) in the directed graph.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or a collection of nodes whose parents are to be retrieved.
        include_self : bool, optional
            Whether to include the node(s) themselves in the result. Default is False.

        Returns
        -------
        SymbolContainer
            The union of the parent nodes.
        """
        
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        
        nodes = {self.syn.get(n, n) for n in nodes}
        
        result = {p for n in nodes for p in self._ctf_graphs.get(n,self).de_graph.predecessors(n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result)

    def get_children(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False
    ):
        """
        Return a SymbolContainer of the children of the given node(s) in the directed graph.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or a collection of nodes whose children are to be retrieved.
        include_self : bool, optional
            Whether to include the node(s) themselves in the result. Default is False.

        Returns
        -------
        SymbolContainer
            The union of the child nodes.
        """

        nodes = set(node) if isinstance(node, (set, list)) else {node}
        
        nodes = {self.syn.get(n, n) for n in nodes}
        
        result = {c for n in nodes for c in self._ctf_graphs.get(n,self).de_graph.successors(n)}
        if include_self:
            result = result.union(nodes)
        return SymbolContainer(result)

    def get_ancestors(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False,
        as_graph: bool = False
    ):
        """
        Return a SymbolContainer or subgraph of the ancestors of the given node(s).

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or a collection of nodes whose ancestors are to be retrieved.
        include_self : bool, optional
            Whether to include the node(s) themselves. Default is False.
        as_graph : bool, optional
            Whether to return the result as a subgraph. Default is False.

        Returns
        -------
        Union[SymbolContainer, CausalGraph]
            A SymbolContainer of the ancestor nodes or a subgraph of those nodes.
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        result = {a for n in nodes for a in nx.ancestors(self._ctf_graphs.get(n,self).de_graph, n)}
        edges = [edge for n in nodes for edge in self._ctf_graphs.get(n,self).de_graph.edges(n) if edge[0] in result and edge[1] in result]
        
        if include_self:
            result = result.union(nodes)
            
        if as_graph:
            return self.__class__(
                v = result,
                directed_edges = edges,
            )
            
        return SymbolContainer(result)

    def get_descendants(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False,
        as_graph: bool = False
    ):
        """
        Return a SymbolContainer or subgraph of the descendants of the given node(s).

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or a collection of nodes whose descendants are to be retrieved.
        include_self : bool, optional
            Whether to include the node(s) themselves. Default is False.
        as_graph : bool, optional
            Whether to return the result as a subgraph. Default is False.

        Returns
        -------
        Union[SymbolContainer, CausalGraph]
            A SymbolContainer of the descendant nodes or a subgraph of those nodes.
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        
        nodes = {self.syn.get(n, n) for n in nodes}
        
        result = {d for n in nodes for d in nx.descendants(self._ctf_graphs.get(n,self).de_graph, n)}
        edges = [edge for n in nodes for edge in self._ctf_graphs.get(n,self).de_graph.edges(n) if edge[0] in result and edge[1] in result]
        
        if include_self:
            result = result.union(nodes)
            
        if as_graph:
            return self.__class__(
                v = result,
                directed_edges = edges,
            )
            
        return SymbolContainer(result)

    def get_neighbors(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], 
        include_self: bool = False,
        as_graph: bool = False
    ):
        """
        Return a SymbolContainer or subgraph of the neighbors in the bidirected graph.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            A node or a collection of nodes whose bidirected neighbors are to be retrieved.
        include_self : bool, optional
            Whether to include the node(s) themselves. Default is False.
        as_graph : bool, optional
            Whether to return the result as a subgraph. Default is False.

        Returns
        -------
        Union[SymbolContainer, CausalGraph]
            A SymbolContainer of neighbor nodes or a subgraph of those nodes.
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        
        nodes = {self.syn.get(n, n) for n in nodes}
        
        result = {nbr for n in nodes for nbr in self._ctf_graphs.get(n,self).be_graph.neighbors(n)}
        edges = [edge for n in nodes for edge in self._ctf_graphs.get(n,self).be_graph.edges(n, keys=False) if edge[0] in result and edge[1] in result]
        if include_self:
            result = result.union(nodes)
            
        if as_graph:
            return self.__class__(
                v = result,
                bidirected_edges = edges,
            )
            
        return SymbolContainer(result)

    def get_connected_components(
        self, 
        node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
        as_graph: bool = False
    ):
        """
        Return connected components containing the given node(s) in the bidirected graph.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Node(s) for which the connected components are to be found.
        as_graph : bool, optional
            Whether to return each component as a subgraph. Default is False.

        Returns
        -------
        Union[List[SymbolContainer], List[CausalGraph]]
            A list of connected components, either as SymbolContainers or subgraphs.
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        
        nodes = {self.syn.get(n, n) for n in nodes}
        
        result = []
        for n in nodes:
            for comp in self._ctf_graphs.get(n,self).cc:
                if comp & nodes:
                    result.append(SymbolContainer(comp))
                
        if as_graph:
            return [self.__class__(
                v = comp,
                bidirected_edges = [edge for edge in self.be_graph.edges(keys=False) if edge[0] in comp and edge[1] in comp],
            ) for comp in result]
                
        return result
    
    
    def get_nodes(self, node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], as_graph: bool = False):
        """
        Return the counterfactual identity of node(s) in the graph.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            The node(s) to retrieve.
        as_graph : bool, optional
            Whether to return the result as a subgraph. Default is False.

        Returns
        -------
        Union[SymbolContainer, Accessors]
            A SymbolContainer of the nodes or a subgraph of those nodes.
        """
        nodes = set(node) if isinstance(node, (set, list)) else {node}
        
        nodes = {self.syn.get(n, n) for n in nodes}
        
        if as_graph:
            return self.__class__(
                v = nodes,
                directed_edges = [edge for edge in self.de_graph.edges if edge[0] in nodes and edge[1] in nodes],
                bidirected_edges = [edge for edge in self.be_graph.edges(keys=False) if edge[0] in nodes and edge[1] in nodes],
            )
        
        return SymbolContainer(nodes)
    
    
    
    def get_ctf_ancestors(self, node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]):
        
        """
        Return counterfactual-aware ancestors for the given node(s),
        removing irrelevant interventions where possible.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Node(s) for which to retrieve counterfactual ancestors.

        Returns
        -------
        SymbolContainer
            The set of counterfactual-adjusted ancestors.
        """
        
        
        node = set(node) if isinstance(node, (set, list)) else {node}
        node = {self.syn.get(n, n) for n in node}
        
        ctf_ancestors = set()
        
        for n in node:
            interventions = n.interventions.keys()
            
            if not interventions:
                ctf_ancestors.update(self.get_ancestors(n, include_self=True))
                continue
            
            do_graph = self._ctf_graphs.get(n,None)
            
            if do_graph is None:
                raise ValueError(f"Node {n} not found in submodels with keys: {self._ctf_graphs.keys()}.")
            
            x = do_graph.get_nodes(list(interventions))
            
            anc = do_graph.get_ancestors(n, include_self=True) - x
            
            for a in anc:
                
                z = [val.main for val in (x & do_graph.get_ancestors(a, include_self=True))]
                
                modified_a = a.remove_interventions([i for i in interventions if str(i) not in z])
                
                ctf_ancestors.add(modified_a)
        
        # Eagerly generate graphs for new counterfactuals
        for n in ctf_ancestors:
            if self._ctf_graphs.get(n,None) is None:
                self.do(n.interventions)

                    
                
                
        return SymbolContainer(ctf_ancestors)
                        
            

        
        
        
    def get_ctf_descendants(self, node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]):
        """
        Return counterfactual-aware descendants for the given node(s),
        removing irrelevant interventions where possible.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Node(s) for which to retrieve counterfactual descendants.

        Returns
        -------
        SymbolContainer
            The set of counterfactual-adjusted descendants.
        """        
        
        
        node = set(node) if isinstance(node, (set, list)) else {node}
        node = {self.syn.get(n, n) for n in node}
        
        ctf_descendants = set()
        
        for n in node:
            interventions = n.interventions.keys()
            
            if not interventions:
                ctf_descendants.update(self.get_descendants(n, include_self=True))
                continue
            
            do_graph = self._ctf_graphs.get(n,None)
            
            if do_graph is None:
                raise ValueError(f"Node {n} not found in submodels with keys: {self._ctf_graphs.keys()}.")
            
            x = do_graph.get_nodes(list(interventions))
            
            desc = do_graph.get_descendants(n, include_self=True) - x
            
            for d in desc:
                
                z = [val.main for val in (x & do_graph.get_descendants(d, include_self=True))]
                
                modified_d = d.remove_interventions([i for i in interventions if str(i) not in z])
                
                ctf_descendants.add(modified_d)
                
        # Eagerly generate graphs for new counterfactuals
        for n in ctf_descendants:
            if self._ctf_graphs.get(n,None) is None:
                self.do(n.interventions)  

                
        return SymbolContainer(ctf_descendants)
    
    def get_ctf_parents(self, node: Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]):
        """
        Return counterfactual-aware parents for the given node(s),
        removing irrelevant interventions where possible.

        Parameters
        ----------
        node : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Node(s) for which to retrieve counterfactual parents.

        Returns
        -------
        SymbolContainer
            The set of counterfactual-adjusted parents.
        """

        
        
        node = set(node) if isinstance(node, (set, list)) else {node}
        node = {self.syn.get(n, n) for n in node}
        
        ctf_parents = set()
        
        for n in node:
            interventions = n.interventions.keys()
            
            if not interventions:
                ctf_parents.update(self.get_parents(n, include_self=True))
                continue
            
            do_graph = self._ctf_graphs.get(n,None)
            
            if do_graph is None:
                raise ValueError(f"Node {n} not found in submodels with keys: {self._ctf_graphs.keys()}.")
            
            x = do_graph.get_nodes(list(interventions))
            
            par = do_graph.get_parents(n, include_self=True) - x
            
            for p in par:
                
                z = [val.main for val in (x & do_graph.get_parents(p, include_self=True))]
                
                modified_p = p.remove_interventions([i for i in interventions if str(i) not in z])
                
                ctf_parents.add(modified_p)
                
        # Eagerly generate graphs for new counterfactuals
        for n in ctf_parents:
            if self._ctf_graphs.get(n,None) is None:
                self.do(n.interventions)

                
        return SymbolContainer(ctf_parents)
