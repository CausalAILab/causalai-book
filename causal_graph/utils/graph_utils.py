import networkx as nx
from typing import List, Dict, Tuple






    

def combine_to_directed(de_graph, be_graph):
    
    combined_graph = nx.MultiDiGraph(de_graph)
    
    i = 0
    for edge in be_graph.edges:
        combined_graph.add_node(f'U{i}',label='exogenous')
        combined_graph.add_edge(f'U{i}', edge[0])
        combined_graph.add_edge(f'U{i}', edge[1])
        i= i + 1
        
    return combined_graph