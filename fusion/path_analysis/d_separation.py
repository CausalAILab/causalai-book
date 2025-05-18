from src.graph.classes.graph_defs import directedEdgeType, bidirectedEdgeType
from src.path_analysis.classes.direction import Direction as PathDirection
from src.path_analysis.classes.path_search import PathSearch

from src.inference.utils.graph_utils import GraphUtils as gu
from src.common.object_utils import ObjectUtils as ou


class DSeparation():

    # Graph, Node[], Node[], Node[]
    # boolean
    @staticmethod
    def test(G, X, Y, Z=[]):
        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        search = DSeparation.getPathSearch(G, X, Y, Z, 'd-con')

        if search is None:
            return True

        return len(search.findPaths(None, 1)) == 0

    # Path[]

    @staticmethod
    def findDConnectedPaths(G, X, Y, Z):
        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        search = DSeparation.getPathSearch(G, X, Y, Z, 'd-con')

        if search is None:
            return []

        return search.findPaths(None, 1e8)

    # Path[]

    @staticmethod
    def findDSeparatedPaths(G, X, Y, Z):
        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        search = DSeparation.getPathSearch(G, X, Y, Z, 'd-sep')

        if search is None:
            return []

        return search.findPaths(None, 1e8)

    # Path[]

    @staticmethod
    def findDConnectedDirectedPaths(G, X, Y, Z):
        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        search = DSeparation.getPathSearch(G, X, Y, Z, 'd-con-directed')

        if search is None:
            return []

        return search.findPaths(None, 1e8)

    # PathSearch

    @staticmethod
    def getPathSearch(G, X, Y, Z, type_='d-con'):
        search = PathSearch(G)

        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        if len(X) == 0 or len(Y) == 0 or (len(X) == 1 and X[0] is None) or (len(Y) == 1 and Y[0] is None):
            return None

        search.sources = X
        search.targets = Y

        observed = DSeparation.getObservedVariables(G, Z)

        if type_ == 'd-sep':
            # search.pathFilter = function (path) { return filterDSeparatedPaths(path, observed.observed, observed.ancestors) }
            search.pathFilter = lambda path: DSeparation.filterDSeparatedPaths(
                path, observed['observed'], observed['ancestors'])
        elif type_ == 'd-con':
            # search.edgeFilter = (graph, node, previous) => this.edgeFilterDConnectedPaths(graph, node, previous, observed.observed, observed.ancestors)
            search.edgeFilter = lambda graph, node, previous: DSeparation.edgeFilterDConnectedPaths(
                graph, node, previous, observed['observed'], observed['ancestors'])
        elif type_ == 'd-con-directed':
            # search.pathFilter = (path) => this.filterDConnectedDirectedPaths(path, observed.observed, observed.ancestors)
            search.pathFilter = lambda path: DSeparation.filterDConnectedDirectedPaths(
                path, observed['observed'], observed['ancestors'])

        return search

    # Path, ObservedNodes, ObservedNodes
    # boolean

    @staticmethod
    def filterDSeparatedPaths(path, observed, ancOfObserved):
        for i in range(1, len(path.edges)):
            prev = path.edges[i - 1]
            curr = path.edges[i]

            isAncOfObs = curr.source in ancOfObserved and ancOfObserved[curr.source] is not None
            isObserved = curr.source in observed and observed[curr.source] is not None

            isPrevDirected = prev.edge['type_'] == directedEdgeType.id_
            isPrevBidirected = prev.edge['type_'] == bidirectedEdgeType.id_
            isPrevIncoming = isPrevBidirected or (
                isPrevDirected and prev.direction == PathDirection.directed)

            isCurrDirected = curr.edge['type_'] == directedEdgeType.id_
            isCurrBidirected = curr.edge['type_'] == bidirectedEdgeType.id_
            isCurrOutgoingDirected = isCurrDirected and curr.direction == PathDirection.directed
            isCurrIncomingDirected = isCurrDirected and curr.direction == PathDirection.reversed

            # closed v-structure
            if isPrevIncoming and not isAncOfObs:
                if isCurrBidirected or isCurrIncomingDirected:
                    return True

            # closed chain
            elif isPrevIncoming and isObserved:
                if isCurrOutgoingDirected:
                    return True

            # closed fork, and reversed chain
            elif not isPrevIncoming and isObserved:
                return True

        return False

    # Graph, Node, PathEdge, ObservedNodes, ObservedNodes
    # Edge[]

    @staticmethod
    def edgeFilterDConnectedPaths(G, node, previous, observed, ancOfObserved):
        edges = []

        isAncOfObs = node['name'] in ancOfObserved and ancOfObserved[node['name']] is not None
        isObserved = node['name'] in observed and observed[node['name']] is not None

        previousIncoming = previous is not None and (
            previous.edge['type_'] == bidirectedEdgeType.id_ or previous.direction == PathDirection.directed)

        if previousIncoming:
            # opened v-structure, closed chain
            # -> X <-  O
            # -> X ->  X
            if isObserved:
                edges = gu.getIncoming(node, G)
            # opened v-structure, opened chain
            # -> O <-  O
            # -> O ->  O
            elif isAncOfObs:
                edges = gu.getIncoming(node, G) + gu.getOutgoing(node, G)
            # closed v-structure, opened chain
            # -> O <-  X
            # -> O ->  O
            elif not isAncOfObs:
                edges = gu.getOutgoing(node, G)
        else:
            # closed fork and chain
            # <- X ->  X
            # <- X <-  X
            # if isObserved:
            #     pass
            # else:
            if not isObserved:
                edges = gu.getIncoming(node, G) + gu.getOutgoing(node, G)

        return edges

    @staticmethod
    def filterDConnectedPaths(path, observed, ancOfObserved):
        for i in range(1, len(path.edges)):
            prev = path.edges[i - 1]
            curr = path.edges[i]

            isAncOfObs = curr.source in ancOfObserved and ancOfObserved[curr.source] is not None
            isObserved = curr.source in observed and observed[curr.source] is not None

            isPrevDirected = prev.edge['type_'] == directedEdgeType.id_
            isPrevBidirected = prev.edge['type_'] == bidirectedEdgeType.id_
            isPrevIncoming = isPrevBidirected or (
                isPrevDirected and prev.direction == PathDirection.directed)

            isCurrDirected = curr.edge['type_'] == directedEdgeType.id_
            isCurrBidirected = curr.edge['type_'] == bidirectedEdgeType.id_
            isCurrOutgoingDirected = isCurrDirected and curr.direction == PathDirection.directed
            isCurrIncomingDirected = isCurrDirected and curr.direction == PathDirection.reversed
            isCurrIncoming = isCurrBidirected or isCurrIncomingDirected

            if isPrevIncoming:
                # opened v-structure, closed chain
                # -> X <-  O
                # -> X ->  X
                if isObserved:
                    if isCurrOutgoingDirected:
                        return False
                # opened v-structure, opened chain
                # -> O <-  O
                # -> O ->  O
                # elif isAncOfObs:
                #     pass
                # closed v-structure, opened chain
                # -> O <-  X
                # -> O ->  O
                elif not isAncOfObs:
                    if isCurrIncoming:
                        return False
            else:
                # closed fork and chain
                # <- X ->  X
                # <- X <-  X
                if isObserved:
                    return False
                # opened fork and chain
                # <- O ->  O
                # <- O <-  O

        return True

    @staticmethod
    def filterDConnectedDirectedPaths(path, observed, ancOfObserved):
        for i in range(1, len(path.edges)):
            prev = path.edges[i - 1]
            curr = path.edges[i]

            isPrevDirectedForward = prev.edge['type_'] == directedEdgeType.id_ and prev.direction == PathDirection.directed
            isCurrDirectedForward = curr.edge['type_'] == directedEdgeType.id_ and curr.direction == PathDirection.directed

            if not isPrevDirectedForward or not isCurrDirectedForward:
                return False

            isAncOfObs = curr.source in ancOfObserved and ancOfObserved[curr.source] is not None
            isObserved = curr.source in observed and observed[curr.source] is not None

            isPrevDirected = prev.edge['type_'] == directedEdgeType.id_
            isPrevBidirected = prev.edge['type_'] == bidirectedEdgeType.id_
            isPrevIncoming = isPrevBidirected or (
                isPrevDirected and prev.direction == PathDirection.directed)

            isCurrDirected = curr.edge['type_'] == directedEdgeType.id_
            isCurrBidirected = curr.edge['type_'] == bidirectedEdgeType.id_
            isCurrOutgoingDirected = isCurrDirected and curr.direction == PathDirection.directed
            isCurrIncomingDirected = isCurrDirected and curr.direction == PathDirection.reversed
            isCurrIncoming = isCurrBidirected or isCurrIncomingDirected

            if isPrevIncoming:
                # opened v-structure, closed chain
                # -> X <-  O
                # -> X ->  X
                if isObserved:
                    if isCurrOutgoingDirected:
                        return False
                # opened v-structure, opened chain
                # -> O <-  O
                # -> O ->  O
                # elif isAncOfObs:
                #     pass
                # closed v-structure, opened chain
                # -> O <-  X
                # -> O ->  O
                elif not isAncOfObs:
                    if isCurrIncoming:
                        return False
            else:
                # closed fork and chain
                # <- X ->  X
                # <- X <-  X
                if isObserved:
                    return False
                # opened fork and chain
                # <- O ->  O
                # <- O <-  O

        return True

    # Graph, Node[]
    # Dict[str, boolean]

    @staticmethod
    def getObservedVariables(G, nodes):
        observed = dict()
        ancObserved = dict()

        for node in nodes:
            observed[node['name']] = True

            ancestors = gu.ancestors(node, G)

            for anc in ancestors:
                ancObserved[anc['name']] = True

        return {
            'observed': observed,
            'ancestors': ancObserved
        }
