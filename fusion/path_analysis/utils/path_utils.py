from functools import partial

from src.graph.classes.graph_defs import directedEdgeType
from src.path_analysis.classes.direction import Direction as PathDirection
from src.path_analysis.classes.path_search import PathSearch
from src.inference.utils.graph_utils import compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.common.object_utils import ObjectUtils as ou
from src.path_analysis.utils.edge_filter import EdgeFilter


class PathUtils():

    @staticmethod
    def findDirectedPaths(graph, source, target, prohibitedIntermediateNodes = [], numPaths = 1e4):
        if not graph or not source or not target:
            return []

        source = ou.makeArray(source)
        target = ou.makeArray(target)
        prohibitedIntermediateNodes = ou.makeArray(prohibitedIntermediateNodes)

        if None in source or None in target or None in prohibitedIntermediateNodes:
            return []

        if numPaths < 1:
            numPaths = 1

        if numPaths > 1e4:
            numPaths = 1e4

        pathSearch = PathSearch(graph, source, target)
        pathSearch.pathFilter = PathUtils.filterForDirectedPath(graph, prohibitedIntermediateNodes)

        return pathSearch.findPaths(None, numPaths)


    # Path[]
    @staticmethod
    def findConfoundingPaths(G, source, target, adjusted = [], numPaths = 1e4):
        if not G or not source or not target:
            return []

        source = ou.makeArray(source)
        target = ou.makeArray(target)
        adjusted = ou.makeArray(adjusted)
        
        if None in source or None in target or None in adjusted:
            return []
        
        if numPaths < 1:
            numPaths = 1

        if numPaths > 1e4:
            numPaths = 1e4

        pathSearch = PathSearch(G, source, target)
        pathSearch.edgeFilter = EdgeFilter.edgeFilterConfoundingPaths(source, adjusted)
        
        return pathSearch.findPaths(None, numPaths)


    # Graph, Node[]
    # boolean
    @staticmethod
    def filterForDirectedPath(G, prohibitedIntermediateNodes):
        return partial(PathUtils._filterForDirectedPath, G, prohibitedIntermediateNodes)


    # Graph, Node[], Path
    # boolean
    @staticmethod
    def _filterForDirectedPath(G, prohibitedIntermediateNodes, path):
        if len(path.edges) == 0:
            return False
        
        for i in range(path.length):
            pathEdge = path.edges[i]
            
            if pathEdge.edge['type_'] != directedEdgeType.id_:
                return False

            if pathEdge.direction == PathDirection.reversed:
                return False

            if i == 0:
                targetNode = gu.getNodeByName(pathEdge.target, G)
                
                if targetNode is None:
                    return False

                if su.belongs(targetNode, prohibitedIntermediateNodes, compareNames):
                    return False
            else:
                sourceNode = gu.getNodeByName(pathEdge.source, G)
                
                if sourceNode is None:
                    return False

                if su.belongs(sourceNode, prohibitedIntermediateNodes, compareNames):
                    return False

        return True