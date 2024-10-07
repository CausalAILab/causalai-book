import itertools
# from path.path_utils import causalPathExists

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import basicNodeType, latentNodeType, undirectedEdgeType
from src.adjustment.adjustment_sets_utils import writeNodeNames
from src.inference.utils.graph_utils import compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils
from src.path_analysis.d_separation import DSeparation
from src.path_analysis.utils.path_utils import PathUtils
from src.common.object_utils import ObjectUtils as ou

from src.error.error_messages import defaultErrorMessage
from src.adjustment.classes.exceptions import AdjustmentSetsError
from src.common.uuid_generator import UUIDGenerator as uuid


# IDs of nodes representing a single group of treatment/outcome
global XmId
global YmId

errors = {
    'treatment': 'Please specify the treatment variable(s).',
    'outcome': 'Please specify the outcome variable(s).',
    'treatmentAndOutcome': 'Please specify the treatment & outcome variables.'
}


class BackdoorAdjustment():
    """
    Provides features related to backdoor adjustment.

    Attributes
    ----------

    Methods
    -------
    listAdmissibleSets(graph, X, Y, Z = [], limit = 1e8)
        Returns a list of admissible sets.
    testAdmissibility(graph, X, Y, Z = [], covariates = [])
        Tests whether a given list of covariates is admissible or not.
    """

    @staticmethod
    def listAdmissibleSets(graph, X, Y, Z=[], limit=1e8):
        """
        Returns a list of admissible sets.

        Parameters
        ----------
        graph : Graph
            A Graph object.
        X : Node | List[Node]
            A list of treatment variables.
        Y : Node | List[Node]
            A list of outcome variables.
        Z : Node | List[Node]
            A list of adjusted variables (default is empty).
        limit: number
            Number of admissible sets to output before the algorithm stops (default is 1e8).

        Returns
        -------
        sets: List[List[Node]]

        Raises
        ------
        AdjustmentSetsError
            An exception including an error message (and witness if any).
        """

        global XmId
        global YmId

        try:
            if not graph or not X or not Y:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)
            Z = ou.makeArray(Z)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            G = ProjectionUtils.unproject(graph)

            # if not causalPathExists(G, X, Y):
            # return {'admissibleSets': []}

            Gpbd = gu.gpbd(G, X, Y)
            AnG = gu.ancestral(Gpbd, X + Y + Z)
            M = gu.moralize(AnG)

            if len(M.nodes) == 0:
                return []

            # change graph to make it suitable to run Takata's

            # add X_m and Y_m
            # reset random Ids
            XmId = uuid.generateRandomId(32)
            YmId = uuid.generateRandomId(32)

            XmNode = {
                'name': XmId,
                'label': XmId
            }
            YmNode = {
                'name': YmId,
                'label': YmId
            }

            M.addNodes([XmNode, YmNode])

            #   add a node: X_m which connects all X
            #   add a node: Y_m which connects all Y
            edgesToAdd = []

            for node in X:
                edgesToAdd.append({
                    'from_': XmId,
                    'to_': node['name'],
                    'type_': undirectedEdgeType.id_
                })

            for node in Y:
                edgesToAdd.append({
                    'from_': YmId,
                    'to_': node['name'],
                    'type_': undirectedEdgeType.id_
                })

            M.addEdges(edgesToAdd)

            #   connect X_m with N(X)
            #   connect Y_m with N(Y)
            NX = gu.neighbors(X, M)
            NY = gu.neighbors(Y, M)

            #   exclude self nodes
            NX = su.difference(NX, [XmNode], 'name')
            NY = su.difference(NY, [YmNode], 'name')

            edgesToAdd = []

            for node in NX:
                edgesToAdd.append({
                    'from_': XmId,
                    'to_': node['name'],
                    'type_': undirectedEdgeType.id_
                })

            for node in NY:
                edgesToAdd.append({
                    'from_': YmId,
                    'to_': node['name'],
                    'type_': undirectedEdgeType.id_
                })

            M.addEdges(edgesToAdd)

            # remove R and connect its neighbors
            edgesToAdd = []

            Dpcp = gu.Dpcp(G, X, Y)
            R = su.union(su.union(X, Y, 'name'), Dpcp, 'name')

            for node in R:
                ns = gu.neighbors(node, M)
                ns = su.difference(ns, R, 'name')

                names = list(map(lambda n: n['name'], ns))
                pairs = [(a, b) for a in names for b in names if b > a]

                for (a, b) in pairs:
                    if gu.hasEdge(a, b, M) or gu.hasEdge(b, a, M):
                        continue

                    edge = {
                        'from_': a,
                        'to_': b,
                        'type_': undirectedEdgeType.id_
                    }

                    edgesToAdd.append(edge)

            M.addEdges(edgesToAdd)
            M.deleteNodes(R)

            A = [XmNode]
            U = gu.neighbors(YmNode, M)
            U.append(YmNode)

            latentNodes = list(
                filter(lambda n: n['type_'] == latentNodeType.id_, G.nodes))
            nodesToExclude = su.union(latentNodes, [YmNode], 'name')

            #   find admissible sets
            minimalSeparators = []
            BackdoorAdjustment.listMinSep(
                M, A, U, minimalSeparators, Z, nodesToExclude, limit)

            admissibleSets = []

            #   remove sets including latent nodes
            for nodes in minimalSeparators:
                intersection = su.intersection(nodes, latentNodes, 'name')

                if len(intersection) == 0:
                    admissibleSets.append(nodes)

            #   remove sets which are not minimum-size
            minSize = float('inf')

            for nodes in admissibleSets:
                if len(nodes) < minSize:
                    minSize = len(nodes)

            admissibleSets = [v for v in admissibleSets if len(v) == minSize]

            #   convert nodes to node names
            sets = []

            for nodes in admissibleSets:
                nodeNames = list(map(lambda n: n['name'], nodes))
                nodeNames.sort()

                sets.append(nodeNames)

            #   this sorts the sets by lex order, but not the labels within each set
            sets.sort()

            #   remove duplicate sets
            #   need to sort before
            #   https://stackoverflow.com/questions/2213923/removing-duplicates-from-a-list-of-lists
            sets = list(k for k, _ in itertools.groupby(sets))

            return sets

        except AdjustmentSetsError as error:
            return {'error': error.__repr__()}
        except:
            return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    @staticmethod
    def listMinSep(G, A, U, minimalSeparators, Z=[], nodesToExclude=[], limit=1e8):
        if len(minimalSeparators) >= limit:
            return

        SA = BackdoorAdjustment.closeSeparator(G, A, Z, nodesToExclude)
        Aexp = BackdoorAdjustment.expansion(G, SA, Z)
        AexpIntersectU = su.intersection(Aexp, U, 'name')

        #   subtree contains new admissible sets
        if len(AexpIntersectU) == 0:
            A = Aexp
            NA = BackdoorAdjustment.actualNeighbors(G, A, Z, nodesToExclude)
            NAMinusU = su.difference(NA, U, 'name')

            if len(NAMinusU) > 0:
                for v in NAMinusU:
                    BackdoorAdjustment.listMinSep(G, su.union(
                        A, [v], 'name'), U, minimalSeparators, Z, nodesToExclude, limit)
                    BackdoorAdjustment.listMinSep(G, A, su.union(
                        U, [v], 'name'), minimalSeparators, Z, nodesToExclude, limit)

            #   leaf: output S(A) - minimal sepset
            else:
                SA = BackdoorAdjustment.closeSeparator(G, A, Z, nodesToExclude)

                minimalSeparators.append(SA)

    #   find close separator of A
    #   - G' = G - N(A)
    #   - Find C (containing b) from G'
    #   - Return N(V(C))

    @staticmethod
    def closeSeparator(G, A, nodesToInclude=[], nodesToExclude=[]):
        global YmId

        YmNode = {
            'name': YmId,
            'type_': basicNodeType.id_
        }

        NA = BackdoorAdjustment.actualNeighbors(
            G, A, nodesToInclude, nodesToExclude)
        VMinusNA = su.difference(G.nodes, su.union(
            NA, nodesToInclude, 'name'), 'name')
        GMinusNA = gu.subgraph(G, VMinusNA)
        CC = GMinusNA.connectedComponents()
        C = None

        for cc in CC:
            if su.belongs(YmNode, cc, compareNames):
                C = cc
                break

        if not C or len(C) == 0:
            return []

        return BackdoorAdjustment.actualNeighbors(G, C, nodesToInclude, nodesToExclude)

    #   find expansion of A
    #   - G' = G - S(A)
    #   - Find C (containing a) from G'
    #   - Return V(C)

    @staticmethod
    def expansion(G, SA, nodesToInclude=[]):
        global XmId

        XmNode = {
            'name': XmId,
            'type_': basicNodeType.id_
        }

        VMinusSA = su.difference(G.nodes, su.union(
            SA, nodesToInclude, 'name'), 'name')
        GMinusSA = gu.subgraph(G, VMinusSA)
        CC = GMinusSA.connectedComponents()
        C = None

        for cc in CC:
            if su.belongs(XmNode, cc, compareNames):
                C = cc
                break

        if not C or len(C) == 0:
            return []

        return C

    # Graph, Node | Node[], Node[], Node[]
    # Node[]

    @staticmethod
    def actualNeighbors(G, V, nodesToInclude=[], nodesToExclude=[]):
        V = ou.makeArray(V)

        if len(V) == 0:
            return []

        visited = dict()

        for node in su.union(V, nodesToInclude, 'name'):
            visited[node['name']] = True

        neighbors = []
        Q = V.copy()

        while len(Q) > 0:
            v = Q.pop()
            N = gu.neighbors(v, G)

            for node in N:
                if node['name'] not in visited:
                    visited[node['name']] = True

                    if su.belongs(node, nodesToExclude, compareNames):
                        Q.append(node)
                    else:
                        neighbors.append(node)

        return neighbors

    @staticmethod
    def printAdmissibleSets(result):
        if result is None:
            return

        if len(result) == 0:
            print('No admissible sets.')
            return

        txt = '' + str(len(result)) + ' admissible set' + \
            ('s' if len(result) > 1 else '') + ':'
        print(txt)

        for adm in result:
            print(writeNodeNames(adm))

    @staticmethod
    def testAdmissibility(graph, X, Y, Z=[], covariates=[]):
        """
        Tests whether a given list of covariates is admissible or not.

        Parameters
        ----------
        graph : Graph
            A Graph object.
        X : Node | List[Node]
            A list of treatment variables.
        Y : Node | List[Node]
            A list of outcome variables.
        Z : Node | List[Node]
            A list of adjusted variables (default is empty).
        covariates : Node | List[Node]
            A list of covariates (default is empty).

        Returns
        -------
        result: dict

        Raises
        ------
        AdjustmentSetsError
            An exception including an error message (and witness if any).
        """

        try:
            if not graph or not X or not Y:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)
            Z = ou.makeArray(Z)
            covariates = ou.makeArray(covariates)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            result = {
                'admissible': BackdoorAdjustment.isAdmissible(graph, X, Y, Z, covariates),
                'conditions': BackdoorAdjustment.getAdmissibilityConditions(graph, X, Y, Z, covariates),
                'covariates': covariates
            }

            return result
        except AdjustmentSetsError as error:
            return {'error': error.__repr__()}
        except:
            return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    @staticmethod
    def isAdmissible(G, X, Y, Z, covariates=[]):
        if not G or not X or not Y:
            return False

        if len(X) == 0 or len(Y) == 0:
            return False

        Gpbd = gu.gpbd(G, X, Y)

        adjusted = su.union(Z, covariates, 'name')
        includesDescX = len(su.intersection(
            gu.descendants(X, G), adjusted, 'name')) > 0

        if includesDescX:
            return False

        return DSeparation.test(Gpbd, X, Y, adjusted)

    @staticmethod
    def getAdmissibilityConditions(G, X, Y, Z, covariates=[]):
        result = [
            {'satisfied': False, 'witness': []},
            {'satisfied': False, 'witness': []}
        ]

        if not G or not X or not Y or len(X) == 0 or len(Y) == 0:
            return result

        adjusted = Z + covariates
        DeX = gu.descendants(X, G)
        ZinDeX = []

        for z in adjusted:
            if su.belongs(z, DeX, compareNames):
                ZinDeX.append(z)

        condition1 = len(ZinDeX) == 0
        result[0]['satisfied'] = condition1

        if not condition1:
            result[0]['witness'] = ZinDeX

        condition2Paths = PathUtils.findConfoundingPaths(G, X, Y, adjusted)
        condition2 = len(condition2Paths) == 0
        result[1]['satisfied'] = condition2

        if not condition2:
            result[1]['witness'] = (G, condition2Paths, adjusted)

        return result
