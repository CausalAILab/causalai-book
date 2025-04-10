from typing import Dict, List, Optional, Set, Union, overload, Tuple



import sympy as sp
import networkx as nx
from graphviz import Source


from symbol_container import SymbolContainer

from causal_graph.display import Display
from causal_graph.dsep import DSeparation
from causal_graph.adjustments import Adjustments
from causal_graph.do_calc import DoCalc
from causal_graph.accessors import Accessors

import causal_graph.utils as utils

from IPython.display import display


class CausalGraph(DSeparation,Adjustments,DoCalc,Display,Accessors):
    """
    _summary_

    Parameters
    ----------
    DSeparation : _type_
        _description_
    Adjustments : _type_
        _description_
    DoCalc : _type_
        _description_
    Display : _type_
        _description_

    Returns
    -------
    _type_
        _description_
    """
    
    @property
    def de_graph(self):
        return self._de
    
    @property
    def be_graph(self):
        return self._be
    
    @property
    def combined_graph(self):
        return self._cdg

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
    
    
    @classmethod
    def from_scm(cls, scm):
        "Instantiate from a SymbolicSCM object"
        
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
                for i in range(len(v_list)):
                    for j in range(i+1,len(v_list)):
                        be.append((v_list[i],v_list[j]))
                    
        
        
        return cls(list(scm.v),de,be)
        

    def __init__(self, v:Optional[List[sp.Symbol]] = None, directed_edges:Optional[List[Tuple[sp.Symbol,sp.Symbol]]] = None,
                 bidirected_edges:Optional[List[Tuple[sp.Symbol,sp.Symbol]]] = None, syn:Optional[Dict[sp.Symbol,sp.Symbol]] = None):
        
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
        self._cdg = nx.MultiDiGraph()
        self._syn = dict(syn)
        self._cc = nx.connected_components(self.be_graph)
        self._interventions = {}

        self.de_graph.add_nodes_from(v)
        self.be_graph.add_nodes_from(v)

        self.de_graph.add_edges_from(directed_edges)
        self.be_graph.add_edges_from(bidirected_edges)
        
        self._cdg = utils.combine_to_directed(self.de_graph,self.be_graph)
    

    def do_x(self, x:Union[sp.Symbol, Set[sp.Symbol]]):
        """
        Do operation on the variable X
        """
        # TODO: Potentially add subscript logic to the do operation
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list)) else [x])}
        
        graph = self.__class__(self.v,
                                [edge for edge in self.de_graph.edges if edge[1] not in x_set],
                                [edge for edge in self.be_graph.edges if edge[0] not in x_set or edge[1] not in x_set])

        return graph
    
    
    def draw(self, node_positions:Optional[Dict[sp.Symbol,Tuple[int,int]]] = None) -> None:
        if node_positions is None:
            node_positions = {}
        src = Source(self.convert_to_dot(node_positions=node_positions),engine="neato")
    
        return display(src)

    def create_intervention(self, nodes:List[sp.Symbol]):
        pass


    

    



