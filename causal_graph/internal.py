from abc import ABC, abstractmethod
from typing import List

import sympy as sp


import networkx as nx



class Internal(ABC):

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
    
    
    def _combine_to_directed(self):
        
        combined_graph = nx.MultiDiGraph(self.de_graph)
        
        i = 0
        for edge in self.be_graph.edges:
            combined_graph.add_node(f'U{i}',label='exogenous')
            combined_graph.add_edge(f'U{i}', edge[0])
            combined_graph.add_edge(f'U{i}', edge[1])
            i= i + 1
            
        return combined_graph
        
    