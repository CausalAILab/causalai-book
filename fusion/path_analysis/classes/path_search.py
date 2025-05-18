from typing import List

from src.graph.classes.graph import Graph
from src.path_analysis.classes.path import Path
from src.path_analysis.classes.path_edge import PathEdge
from src.path_analysis.classes.direction import Direction as PathDirection
from src.inference.utils.graph_utils import compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su


class PathSearch():

    backtrack = 1
    forward = 0
    paths = List[Path]
    graph = Graph
    # sources = List[Node]
    # targets = List[Node]
    # edgeFilter: (graph: Graph, node: Node, previousInPath: PathEdge) => Edge[]
    # pathFilter: (path: Path) => boolean

    def __init__(self, graph, sources = [], targets = []):
        self.graph = graph
        self.sources = sources
        self.targets = targets
        self.edgeFilter = filterAllEdges
        self.pathFilter = filterAllPaths


    # Path, number
    # Path[]
    def findPaths(self, lastPath, limit):
        
        self.paths = []
        mode = self.forward
        lastSource = None
        visited = dict()
        
        currentPath = Path([])

        if lastPath is not None and lastPath.length > 0:
            # make a copy of the passed path
            currentPath.copy(lastPath)

            # if the current path is not empty construct a corresponding visited record
            for edge in currentPath.edges:
                visited[edge.target] = True

            lastSource = currentPath.edges[0].source
            visited[currentPath.edges[0].source] = True
            visited[currentPath.lastEdge.target] = True
            mode = self.backtrack

        while limit > 0:
            if mode == self.forward:
                if currentPath.length == 0:
                    # if the path is empty
                    # let bracktrack pick a source and insert an edge in the path to follow
                    mode = self.backtrack
                else:
                    # the path is not empty; look at the last edge
                    lastEdge = currentPath.lastEdge

                    # mark the node reached by this edge
                    visited[lastEdge.source] = True

                    # have we reached a target?
                    if self.isTarget(gu.getNodeByName(lastEdge.target, self.graph)):
                        # target reached
                        if not self.pathFilter or self.pathFilter(currentPath):
                            self.savePath(currentPath)
                            limit = limit - 1

                        mode = self.backtrack
                    else:
                        # can we move forward?
                        nextEdge = self.getEdgeAfter(gu.getNodeByName(lastEdge.target, self.graph), lastEdge, None, visited)
                        
                        if nextEdge is not None:
                            currentPath.push(nextEdge)
                        else:
                            # backtrack if no further advance can be made in this path
                            mode = self.backtrack

            if mode == self.backtrack:
                if currentPath.length == 0:
                    # the path is empty
                    # find the last source we started from
                    sourceIdx = len(self.sources) - 1 - self.sources[::-1].index(lastSource) if lastSource is not None else -1
                    
                    # unmark the last source
                    # node?
                    if lastSource is not None:
                        if lastSource['name'] in visited:
                            del visited[lastSource['name']]
                    
                    # are there more sources?
                    if len(self.sources) > sourceIdx + 1:
                        # set the new 'lastSource'
                        lastSource = self.sources[sourceIdx + 1]

                        # does it have outgoing edges?
                        nextEdge = self.getEdgeAfter(lastSource, None, None, visited)
                        
                        if nextEdge is not None:
                            currentPath.push(nextEdge)
                            mode = self.forward

                        # if it does not just let the next iteration to pick the next source
                    else:
                        # no more source, we are done
                        break
                else:
                    # path not empty, get and remove the last edge
                    lastEdge = currentPath.pop()

                    # unmark the last node
                    if lastEdge.target in visited:
                        del visited[lastEdge.target]

                    # get the previous edge in the path
                    previousInPath = currentPath.lastEdge

                    # determine next edge to try
                    source = gu.getNodeByName(lastEdge.source, self.graph)
                    nextEdge = self.getEdgeAfter(source, previousInPath, lastEdge, visited)
                    
                    if nextEdge is not None:
                        # if there is a next edge add it to the path
                        currentPath.push(nextEdge)
                        mode = self.forward

                    # if there is no next edge let the next iteration pick a new source

        return self.paths


    # Node, PathEdge, PathEdge, Dict
    # PathEdge
    def getEdgeAfter(self, node, previousInPath, previouslySelected = None, visited = dict()):
        if not self.edgeFilter or not node:
            return None
        
        edges = self.edgeFilter(self.graph, node, previousInPath)
        index = 0
        
        if len(edges) == 0:
            return None

        if previouslySelected is not None:
            # move the iterator right to the previous edge
            # while edges[index] != previouslySelected.edge:
            prevEdge = previouslySelected.edge
            currEdge = edges[index]

            # while index < len(edges) - 1 and not (currEdge['from_'] == prevEdge['from_'] and currEdge['to_'] == prevEdge['to_'] and currEdge['type_'] == prevEdge['type_']):
            while index < len(edges) and not (currEdge['from_'] == prevEdge['from_'] and currEdge['to_'] == prevEdge['to_'] and currEdge['type_'] == prevEdge['type_']):
                index = index + 1

                if index < len(edges):
                    currEdge = edges[index]

            # move onto the next one
            index = index + 1

        if index >= len(edges):
            return None
        
        # move forward up to a non-visited edge
        nodeName = edges[index]['from_'] if edges[index]['to_'] == node['name'] else edges[index]['to_']
        
        # while index < len(edges) - 1 and nodeName in visited:
        while index < len(edges) and nodeName in visited:
            index = index + 1

            if index < len(edges):
                nodeName = edges[index]['from_'] if edges[index]['to_'] == node['name'] else edges[index]['to_']
        
        if index >= len(edges):
            return None
        else:
            direction = PathDirection.reversed if edges[index]['to_'] == node['name'] else PathDirection.directed

            return PathEdge(edges[index], direction)


    # Node
    # boolean
    def isTarget(self, node):
        if node is None:
            return False

        return su.belongs(node, self.targets, compareNames)


    def savePath(self, path):
        pathObj = Path()
        pathObj.copy(path)
        self.paths.append(pathObj)


def filterAllPaths(path):
    return True

def filterAllEdges(graph, node, previous):
    return gu.getOutgoing(node, graph) + gu.getIncoming(node, graph)