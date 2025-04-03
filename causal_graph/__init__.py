from typing import Dict, List, Optional, Union, overload, Tuple


import sympy as sp
import networkx as nx
from graphviz import Source


from symbol_container import SymbolContainer
from scm import SymbolicSCM

from causal_graph.display import Display
from causal_graph.dsep import DSeparation
from causal_graph.adjustments import Adjustments
from causal_graph.do_calc import DoCalc

from IPython.display import display


class CausalGraph(DSeparation,Adjustments,DoCalc,Display):
    
    @property
    def de_graph(self):
        return self._de
    
    @property
    def be_graph(self):
        return self._be

    @property
    def v(self):
        return self._v
    
    @property
    def syn(self):
        # Mapping from a symbol to its counterfactual variant
        return self._syn
    
    @property
    def cc(self):
        return self._cc


    def from_file(self, path:str) -> None:
        "Instantiate from a prestructured .cg file"
        pass
    
    def from_scm(self, obj:SymbolicSCM) -> None:
        "Instantiate from a SymbolicSCM object"
        pass
        

    def __init__(self, v:List[sp.Symbol] = [],  directed_edges:List[Tuple[sp.Symbol,sp.Symbol]] = [],
                 bidirected_edges:List[Tuple[sp.Symbol,sp.Symbol]] = [],syn:Dict[sp.Symbol,sp.Symbol] = {}) -> None:
        

        test_graph = nx.DiGraph()
        test_graph.add_nodes_from(v)
        test_graph.add_edges_from(directed_edges)

        assert nx.is_directed_acyclic_graph(test_graph), "Directed edges cannot form a cycle"
        
        self._v = SymbolContainer(v,syn)
        self._de = nx.DiGraph()
        self._be = nx.Graph()
        self._syn = dict(syn)
        self._cc = nx.connected_components(self.be_graph)
        self._interventions = {}

        self.de_graph.add_nodes_from(v)
        self.be_graph.add_nodes_from(v)

        self.de_graph.add_edges_from(directed_edges)
        self.be_graph.add_edges_from(bidirected_edges)
    

        




    def get_parents(self, node:sp.Symbol):
        return SymbolContainer(self.de_graph.predecessors(node),self.syn)
    
    def get_children(self, node:sp.Symbol):
        return SymbolContainer(self.de_graph.successors(node),self.syn)
    
    def get_ancestors(self, node:sp.Symbol):
        return SymbolContainer(nx.ancestors(self.de_graph, node),self.syn)
    
    def get_neighbors(self, node:sp.Symbol):
        return SymbolContainer(self.be_graph.neighbors(node),self.syn)
    
    def get_connected_component(self, node:sp.Symbol):
        return SymbolContainer([c for c in self.cc if node in c][-1],self.syn)
    
    
    def draw(self, node_positions:Dict[sp.Symbol,Tuple[int,int]] = {}) -> None:
        src = Source(self.convert_to_dot(node_positions=node_positions),engine="neato")
    
        return display(src)
    

    def create_intervention(self, nodes:List[sp.Symbol]):
        pass


    

    #TODO: Consider how to differentiate methods that affect the object and those that return a new object
    

    



