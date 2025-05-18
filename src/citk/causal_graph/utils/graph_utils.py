import networkx as nx
from typing import List, Dict, Tuple

from src.sympy_classes import Variable, variables





    

def combine_to_directed(de_graph, be_graph):
    
    combined_graph = nx.DiGraph(de_graph)
    u = set()
    
    for edge in be_graph.edges(keys=False):
        ordered_edge = sorted(list(edge), key=lambda s: s.name)
        if ordered_edge[0].main == ordered_edge[1].main:
            node_name = f"U{ordered_edge[0].main}"
        else:
            node_name = f"U{''.join([str(ordered_edge[0].main), str(ordered_edge[1].main)])}"
            
        u_var = variables(f'{node_name}')
        
        if not combined_graph.has_node(u_var):
            u.add(u_var)
            combined_graph.add_node(u_var,type='exogenous')
            
        combined_graph.add_edge(u_var, edge[0])
        combined_graph.add_edge(u_var, edge[1])
        
    return combined_graph, u