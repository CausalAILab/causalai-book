from typing import Dict, List, Optional, Set, Union, overload, Tuple



import sympy as sp
import networkx as nx
from graphviz import Source


from src.return_classes import SymbolContainer

from src.causal_graph.display import Display
from src.causal_graph.dsep import DSeparation
from src.causal_graph.adjustments import Adjustments
from src.causal_graph.do_calc import DoCalc
from src.causal_graph.accessors import Accessors

import src.causal_graph.utils as utils

from IPython.display import display


class CausalGraph(DSeparation, Adjustments, DoCalc, Display, Accessors):
    """
    Representation of a causal graph combining directed, bidirected, d‑separation,
    adjustment criteria, do‑calculus, and display functionality.

    Parameters
    ----------
    v : Optional[List[sp.Symbol]]
        List of graph nodes (endogenous variables). Defaults to empty list.
    directed_edges : Optional[List[Tuple[sp.Symbol, sp.Symbol]]]
        List of directed edges (X → Y). Defaults to none.
    bidirected_edges : Optional[List[Tuple[sp.Symbol, sp.Symbol]]]
        List of bidirected edges (X ↔ Y). Defaults to none.
    syn : Optional[Dict[sp.Symbol, sp.Symbol]]
        Mapping from each variable to its counterfactual synonym. Defaults to none.
    """

    @property
    def de_graph(self) -> nx.DiGraph:
        """
        Directed causal graph.

        Returns
        -------
        nx.DiGraph
            A directed acyclic graph whose edges represent direct causal relationships.
        """
        return self._de

    @property
    def be_graph(self) -> nx.Graph:
        """
        Bidirected causal graph.

        Returns
        -------
        nx.Graph
            An undirected graph whose edges represent unobserved confounding between variables.
        """
        return self._be

    @property
    def combined_graph(self) -> nx.DiGraph:
        """
        Combined causal graph.

        Returns
        -------
        nx.DiGraph
            A directed graph merging directed edges (from endogenous variables) and
            bidirected edges (from unobserved confounding) using instantiated exogenous nodes.
        """
        return self._cdg

    @property
    def v(self) -> SymbolContainer:
        """
        Variables in the graph.

        Returns
        -------
        SymbolContainer
            Container of all endogenous variable symbols in the causal graph.
        """
        return self._v

    @property
    def syn(self) -> Dict[sp.Symbol, sp.Symbol]:
        """
        Synonym mapping.

        Returns
        -------
        Dict[sp.Symbol, sp.Symbol]
            Maps each variable to its counterfactual or synonymous symbol.
        """
        return self._syn

    @property
    def cc(self) -> List[Set[sp.Symbol]]:
        """
        Connected components of the bidirected graph.

        Returns
        -------
        List[Set[sp.Symbol]]
            A list of sets, each representing a connected component under bidirected edges.
        """
        return list(self._cc)



    def from_file(self, path:str) -> None:
        
        # TODO
        
        """
        Instantiate a CausalGraph from a prestructured .cg file.

        Parameters
        ----------
        path : str
            Path to the .cg file that describes the causal graph.

        Returns
        -------
        None
        """
        pass
    
    
    @classmethod
    def from_scm(cls, scm):
        """
        Create a CausalGraph from a SymbolicSCM object.

        Parameters
        ----------
        scm : SymbolicSCM
            A symbolic structural causal model.

        Returns
        -------
        CausalGraph
            A new causal graph instance derived from the SCM.
        """
        
        collection = {} # Dictionary collecting the endogenous variables each exogenous variable affects
        
        de = []
        be = []
        
        for s in list(scm.f):
            symbols = scm.f[s].atoms(sp.Symbol)
            
            for symbol in symbols:        
                if symbol in scm.v:
                    de.append((symbol, s))
                    
                if symbol in scm.u:
                    collection.setdefault(symbol, []).append(s)
                    
        for v_list in collection.values():
            if len(v_list) > 1:
                for i,v_i in enumerate(v_list):
                    for v_j in v_list[i+1:]:
                        be.append((v_i,v_j))
                    
        
        
        g = cls(list(scm.v),de,be,scm.syn)
        g._ctf_graphs = {k:sub_scm.graph for k,sub_scm in scm._counterfactuals.items() if sub_scm is not scm}
        
        
        return g
        

    def __init__(self, v:Optional[List[sp.Symbol]] = None, directed_edges:Optional[List[Tuple[sp.Symbol,sp.Symbol]]] = None,
                 bidirected_edges:Optional[List[Tuple[sp.Symbol,sp.Symbol]]] = None, syn:Optional[Dict[sp.Symbol,sp.Symbol]] = None):
        """
        Initialize a CausalGraph with nodes and edges.

        Parameters
        ----------
        v : Optional[List[sp.Symbol]]
            List of endogenous variables (nodes). Defaults to empty list.
        directed_edges : Optional[List[Tuple[sp.Symbol, sp.Symbol]]]
            List of directed edges (X → Y). Defaults to [], must not form a cycle.
        bidirected_edges : Optional[List[Tuple[sp.Symbol, sp.Symbol]]]
            List of bidirected edges (X ↔ Y). Defaults to [], no self‑loops.
        syn : Optional[Dict[sp.Symbol, sp.Symbol]]
            Mapping from each variable to its counterfactual synonym. Defaults to {}.

        Raises
        ------
        AssertionError
            If any directed edge forms a cycle or refers to unknown nodes,
            or if any bidirected edge is a self‑loop or refers to unknown nodes.
        """
        
        
        v = v or []
        directed_edges = directed_edges or []
        bidirected_edges = bidirected_edges or []
        syn = syn or {}
        

        for edge in bidirected_edges:
            assert edge[0] != edge[1], "Bidirected edges cannot be self-loops"
            assert edge[0] in v, f"Node {edge[0]} not in variable list"
            assert edge[1] in v, f"Node {edge[1]} not in variable list"
            
        for edge in directed_edges:
            assert edge[0] != edge[1], "Directed edges cannot be self-loops"
            assert edge[0] in v, f"Node {edge[0]} not in variable list"
            assert edge[1] in v, f"Node {edge[1]} not in variable list"
            

        test_graph = nx.DiGraph()
        test_graph.add_nodes_from(v)
        test_graph.add_edges_from(directed_edges)

        assert nx.is_directed_acyclic_graph(test_graph), "Directed edges cannot form a cycle"
        
        self._v = SymbolContainer(v,syn)
        self._de = nx.DiGraph()
        self._be = nx.Graph()
        self._cdg = nx.DiGraph()
        self._syn = dict(syn)
        self._cc = nx.connected_components(self.be_graph)

        self.de_graph.add_nodes_from(v)
        self.be_graph.add_nodes_from(v)

        self.de_graph.add_edges_from(directed_edges)
        self.be_graph.add_edges_from(bidirected_edges)
        
        self._cdg = utils.combine_to_directed(self.de_graph,self.be_graph)
        
        self._intervention_memo = {}
        self._ctf_graphs = {}
        
        
    def __and__(self, other):
        """
        Compute the intersection of two causal graphs.

        Parameters
        ----------
        other : CausalGraph
            Another causal graph with the same variable set.

        Returns
        -------
        CausalGraph
            A new graph containing only edges present in both graphs.

        Raises
        ------
        AssertionError
            If `other` is not a CausalGraph.
        ValueError
            If the variable sets differ.
        """
        assert isinstance(other, CausalGraph), "Can only combine with another CausalGraph"
        
        if self.v != other.v:
            raise ValueError("Cannot combine graphs with different symbols")
        
        combined = self.__class__(self.v,
                                  set(self.de_graph.edges) & set(other.de_graph.edges),
                                  set(self.be_graph.edges) & set(other.be_graph.edges),
                                self.syn)
        
        return combined
    
    
    def __or__(self, other):
        """
        Compute the union of two causal graphs.

        Parameters
        ----------
        other : CausalGraph
            Another causal graph with the same variable set.

        Returns
        -------
        CausalGraph
            A new graph containing all edges from either graph.

        Raises
        ------
        AssertionError
            If `other` is not a CausalGraph.
        ValueError
            If the variable sets differ.
        """
        assert isinstance(other, CausalGraph), "Can only combine with another CausalGraph"
        
        if self.v != other.v:
            raise ValueError("Cannot combine graphs with different symbols")
        
        combined = self.__class__(self.v,
                                  set(self.de_graph.edges) | set(other.de_graph.edges),
                                  set(self.be_graph.edges) | set(other.be_graph.edges),
                                  self.syn)
        
        return combined
        
    

    def do(self, x:Union[sp.Symbol, Set[sp.Symbol]]):
        """
        Apply a do‑intervention by removing incoming edges to X.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Variable or set of variables to intervene upon.

        Returns
        -------
        CausalGraph
            A new graph after performing the intervention.
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else [x])}
        
        key = hash(tuple(sorted(x_set, key=lambda s: str(s))))
        if key in self._intervention_memo:
            return self._intervention_memo[key]
        
        
        assert all([x in self.v for x in x_set]), f"Cannot do intervention on {x_set} as it is not in the graph"

        vs = {k: sp.Symbol(f"{{{k}}}_{{{utils.format_set(x_set)}}}") for k in self.v}
        
        self._intervention_memo[key] = graph = self.__class__(
                                {vs[n] for n in self.v},
                                [(vs[edge[0]], vs[edge[1]]) for edge in self.de_graph.edges if edge[1] not in x_set],
                                [(vs[edge[0]], vs[edge[1]]) for edge in self.be_graph.edges if edge[0] not in x_set or edge[1] not in x_set],
                                {**self.syn,**vs}
                                )
        
        ctfs = {n: graph for n in graph.v}
        assert set(ctfs).isdisjoint(self._ctf_graphs.keys()), (
            ctfs,
            self._ctf_graphs
            
        )
        
        self._ctf_graphs.update(ctfs)

        return graph
    
    
    def draw(self, node_positions:Optional[Dict[sp.Symbol,Tuple[int,int]]] = None) -> None:
        """
        Render the causal graph using Graphviz.

        Parameters
        ----------
        node_positions : Optional[Dict[sp.Symbol, Tuple[int,int]]], optional
            Mapping of nodes to fixed (x, y) positions for layout. Defaults to None.

        Returns
        -------
        None
        """
        
        if node_positions is None:
            node_positions = {}
        src = Source(self.convert_to_dot(node_positions=node_positions),engine="neato")
    
        return display(src)



    

    



