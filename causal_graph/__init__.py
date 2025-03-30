from typing import Dict, List, Optional, Union, overload, Tuple

from scm import SymbolicSCM

import sympy as sp

import networkx as nx

from symbol_container import SymbolContainer

from causal_graph.dsep import DSeparation

from causal_graph.adjustments import Adjustments

from causal_graph.do_calc import DoCalc


class CausalGraph(DSeparation,Adjustments,DoCalc):


    @overload
    def __init__(self, path:str) -> None:
        "Instantiate from a prestructured .cg file"
        pass
    
    @overload
    def __init__(self, obj:SymbolicSCM) -> None:
        "Instantiate from a SymbolicSCM object"
        pass
        

    @overload
    def __init__(self, V:List[sp.Symbol] = [],  directed_edges:List[Tuple[sp.symbol,sp.symbol]] = [],
                 bidirected_edges:List[Tuple[sp.symbol,sp.symbol]] = [],syn:Dict[sp.Symbol,sp.Symbol] = {}) -> None:
        pass


    
    def __init__(self, *args, **kwargs):

        
        @property
        def de_graph(self):
            return nx.DiGraph()
        
        @property
        def be_graph(self):
            return nx.Graph()

        @property
        def v(self):
            return SymbolContainer()
        
        @property
        def syn(self):
            # Two-way lookup map between symbols and their intervened variants
            return {}
        
        @property
        def cc(self):
            return set(set())
        
        if isinstance(args[0], SymbolicSCM) and not kwargs:

            #TODO: Instantiate from SymbolicSCM

            pass


        else:

            test_graph = nx.DiGraph()
            test_graph.add_nodes_from(args[0])
            test_graph.add_edges_from(args[1])

            assert nx.is_directed_acyclic_graph(test_graph), "Directed edges cannot form a cycle"

            self.de_graph.add_nodes_from(args[0])
            self.be_graph.add_nodes_from(args[0])

            self.de_graph.add_edges_from(args[1])
            self.be_graph.add_edges_from(args[2])
        

            self.syn = dict(kwargs.get('syn', args[3]))

            self.v = SymbolContainer(kwargs.get('V', args[0]),self.syn)

            self.cc = nx.connected_components(self.be_graph) # Disjoint sets of nodes

        




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
    
    
    def _repr_mimebundle_(self, **kwargs):
        pass
    

    def create_intervention(self, nodes:List[sp.Symbol]):
        pass


    

    #TODO: Consider how to differentiate methods that affect the object and those that return a new object
    

    



