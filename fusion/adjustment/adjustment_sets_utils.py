from src.graph.classes.graph_defs import directedEdgeType, bidirectedEdgeType
from src.selection_bias.classes.selection_bias import selectionBiasNodeType
from src.transportability.classes.transportability import transportabilityNodeType
from src.path_analysis.classes.path import Path
from src.path_analysis.classes.direction import Direction as PathDirection
from src.inference.utils.graph_utils import compareNames

from src.path_analysis.d_separation import DSeparation

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.common.object_utils import ObjectUtils as ou


def TestSep(G, X, Y, Z=[]):
    X = ou.makeArray(X)
    Y = ou.makeArray(Y)
    Z = ou.makeArray(Z)

    # Bayes Ball
    # https://github.com/lingxuez/bayes-net/blob/9ba18d08f85d04b566c6a103be67242eab8dc95a/src/BN.py#L114
    AnZ = gu.ancestors(Z, G)

    Q = []

    for x in X:
        Q.append((x['name'], 'up'))

    visited = set()

    while len(Q) > 0:
        (name, dir) = Q.pop()
        node = gu.getNodeByName(name, G)

        if (name, dir) not in visited:
            visited.add((name, dir))

            if not su.belongs(node, Z, compareNames) and su.belongs(node, Y, compareNames):
                return False

            if dir == 'up' and not su.belongs(node, Z, compareNames):
                for parent in G.parents(node):
                    Q.append((parent['name'], 'up'))

                for child in G.children(node):
                    Q.append((child['name'], 'down'))

            elif dir == 'down':
                if not su.belongs(node, Z, compareNames):
                    for child in G.children(node):
                        Q.append((child['name'], 'down'))

                if su.belongs(node, Z, compareNames) or su.belongs(node, AnZ, compareNames):
                    for parent in G.parents(node):
                        Q.append((parent['name'], 'up'))

    return True


def FindSep(G, X, Y, I, R):
    X = ou.makeArray(X)
    Y = ou.makeArray(Y)
    I = ou.makeArray(I)
    R = ou.makeArray(R)

    XY = su.union(X, Y, 'name')
    XYI = su.union(XY, I, 'name')
    Rprime = su.difference(R, XY, 'name')
    Z = su.intersection(Rprime, gu.ancestors(XYI, G), 'name')

    if TestSep(G, X, Y, Z):
        return Z
    else:
        return None


# Graph
# Node


def getSelectionBiasNode(G):
    if not G:
        return None

    nodes = list(filter(lambda n: n['type_'] ==
                 selectionBiasNodeType.id_, G.nodes))

    return nodes[0] if len(nodes) > 0 else None


# Graph
# Node[]
def getSelectionNodes(G):
    if not G:
        return []

    return list(filter(lambda n: n['type_'] == transportabilityNodeType.id_, G.nodes))


# Graph, Path[], Node[]
def getViolatingPathEntries(G, paths, covariates):
    subpaths = []

    AnAdjusted = gu.ancestors(covariates, G)

    for path in paths:
        subpath = Path()

        for i in range(1, path.length):
            targets = []

            prev = path.edges[i - 1]
            curr = path.edges[i]
            intermediateNode = gu.getNodeByName(curr.source, G)

            isPrevDirected = prev.edge['type_'] == directedEdgeType.id_
            isPrevBidirected = prev.edge['type_'] == bidirectedEdgeType.id_
            isPrevIncomingDirected = isPrevDirected and prev.direction == PathDirection.directed

            isCurrDirected = curr.edge['type_'] == directedEdgeType.id_
            isCurrBidirected = curr.edge['type_'] == bidirectedEdgeType.id_
            isCurrIncomingDirected = isCurrDirected and curr.direction == PathDirection.reversed

            isCollider = (
                (isPrevBidirected and isCurrBidirected)
                or (isPrevBidirected and isCurrIncomingDirected)
                or (isPrevIncomingDirected and isCurrIncomingDirected)
                or (isPrevIncomingDirected and isCurrBidirected)
            )

            if isCollider and su.belongs(intermediateNode, AnAdjusted, compareNames):
                DeNode = gu.descendants(intermediateNode, G)
                adjustedDeNode = su.intersection(covariates, DeNode, 'name')

                if len(adjustedDeNode) > 0:
                    for target in adjustedDeNode:
                        targets.append(target)

            if len(targets) > 0:
                pathEdgesToAdd = []

                for target in targets:
                    dconPaths = DSeparation.findDConnectedDirectedPaths(
                        G, [intermediateNode], [target], covariates)

                    if len(dconPaths) > 0:
                        for openPath in dconPaths:
                            pathEdgesToAdd.extend(openPath.edges)

                subpath.edges = pathEdgesToAdd

        subpaths.append(subpath)

    pathEntries = []

    for i in range(len(paths)):
        pathEntry = {
            'path': paths[i],
            'subpaths': [subpaths[i]]
        }

        pathEntries.append(pathEntry)

    return pathEntries


def writeNodeNames(nodes):
    return ', '.join(nodes) if len(nodes) > 0 else 'emptyset'


def nodeNamesToString(nodes, sortByName = True):
    names = list(map(lambda n: n['name'] if n is not None and 'name' in n else '\emptyset', nodes))

    if sortByName:
        names = sorted(names)

    return writeNodeNames(names)


def printAdmissibilityTestResult(result):
    if 'covariates' in result:
        covariates = list(map(lambda n: n['name'], result['covariates']))

        print('Covariates: ' + writeNodeNames(covariates))

    if 'externalData' in result:
        externalData = list(map(lambda n: n['name'], result['externalData']))

        print('External data: ' + writeNodeNames(externalData))

    if 'observations' in result:
        observations = list(
            map(lambda n: n['name'].lower(), result['observations']))

        print('Available P^*(v): P^*(' + writeNodeNames(observations) + ')')

    if 'admissible' in result:
        print('Admissible: ' + str(result['admissible']))

    if 'conditions' in result:
        conds = result['conditions']

        i = 1
        for cond in conds:
            line = 'Condition ' + str(i) + ': ' + str(cond['satisfied'])

            print(line)

            i = i + 1
