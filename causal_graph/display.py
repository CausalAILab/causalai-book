from typing import Dict, List, Optional, Union, overload, Tuple

import networkx as nx
import sympy as sp

from symbol_container import SymbolContainer

class Display:
    
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
        # Mapping from a symbol to its counterfactual variant
        return {}
    
    @property
    def cc(self):
        return set(set())
    
    
    def convert_to_dot(self, node_positions:Dict[sp.Symbol,Tuple[int,int]]={}):
        
        _node_positions = {
            self.syn.get(node, node): pos
            for node, pos in node_positions.items()
        }
        
        dot_str = "digraph G {\n  rankdir=LR;\n"
        
        for node in self.v:
            
            pos = (
                f'pos="{_node_positions[node][0]},{_node_positions[node][1]}!"'
                if node in _node_positions.keys()
                else ""
            )
            fillcolor = "style=filled, fillcolor=lightgray"
            dot_str += f'  {node} [label="{node}" {pos} {fillcolor}];\n'
            
        for edge in [*self.de_graph.edges, *self.be_graph.edges]:
            style = f"penwidth=2.0"
            
            arrow_type = (
                f"[dir=both, style=dashed, constraint=false, splines=curved, {style}]"
                if edge in self.be_graph.edges
                else f"[{style}]"
            )
            
            dot_str += f'  {edge[0]} -> {edge[1]} {arrow_type};\n'
            
        return dot_str + "}"
            
        
        
        
        