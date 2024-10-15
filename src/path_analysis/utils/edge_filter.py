from functools import partial

from src.inference.utils.graph_utils import GraphUtils as gu
from src.path_analysis.d_separation import DSeparation


class EdgeFilter():

    # Node[], Node[]
    # Edge[]
    @staticmethod
    def edgeFilterConfoundingPaths(source, adjusted):
        return partial(EdgeFilter._edgeFilterConfoundingPaths, source, adjusted)


    # Node[], Node[], Graph, Node, PathEdge
    # Edge[]
    @staticmethod
    def _edgeFilterConfoundingPaths(source, adjusted, graph, node, previous):
        # ignore any path where a source node is in the middle
        if node in source and previous is not None:
            return []

        edges = []

        if node in source and previous is None:
            edges = gu.getIncoming(node, graph)
        else:
            edges = EdgeFilter._edgeFilterDConnectedPaths(adjusted, graph, node, previous)
        
        return edges


    @staticmethod
    def _edgeFilterDConnectedPaths(adjusted, graph, node, previous):
        obs = DSeparation.getObservedVariables(graph, adjusted)
        
        return DSeparation.edgeFilterDConnectedPaths(graph, node, previous, obs['observed'], obs['ancestors'])