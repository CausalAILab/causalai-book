from typing import List

from src.path_analysis.classes.path_edge import PathEdge


class Path():

    edges = List[PathEdge]

    def __init__(self, edges = []):
        if edges is None:
            self.edges = []
        else:
            self.edges = edges

    @property
    def length(self):
        return len(self.edges)

    @property
    def lastNode(self):
        return self.lastEdge.target

    @property
    def lastEdge(self):
        if len(self.edges) <= 0:
            return None

        return self.edges[self.length - 1]

    @property
    def graphEdges(self):
        edges = []
        
        for edge in self.edges:
            edges.append(edge.edge)

        return edges
    
    def copy(self, otherPath):
        self.edges = otherPath.edges.copy()

    def push(self, edge):
        self.edges.append(edge)

    def pop(self):
        return self.edges.pop()