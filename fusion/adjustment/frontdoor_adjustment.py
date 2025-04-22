import itertools
import time

from src.graph.classes.graph_defs import basicNodeType, latentNodeType, bidirectedEdgeType
from src.adjustment.adjustment_sets_utils import writeNodeNames, TestSep
from src.inference.utils.graph_utils import compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils
from src.path_analysis.d_separation import DSeparation
from src.common.object_utils import ObjectUtils as ou

from src.error.error_messages import defaultErrorMessage
from src.adjustment.classes.exceptions import AdjustmentSetsError


errors = {
    'treatment': 'Please specify the treatment variable(s).',
    'outcome': 'Please specify the outcome variable(s).',
    'treatmentAndOutcome': 'Please specify the treatment & outcome variables.',
    'IinR': '\'I\' must be a subset or equal to \'R\'.',
    'treatmentInI': '\'I\' cannot include treatment variable(s).',
    'outcomeInI': '\'I\' cannot include outcome variable(s).',
    'treatmentInR': '\'R\' cannot include treatment variable(s).',
    'outcomeInR': '\'R\' cannot include outcome variable(s).',
}


class FrontdoorAdjustment():
    """
    Provides features related to front-door adjustment.

    Attributes
    ----------

    Methods
    -------
    FindFDSet(G, X, Y, I = [], R = [])
        Returns an admissible set.
    ListFDSets(G, X, Y, I = [], R = [], limit = 1e8)
        Returns a list of admissible sets.
    testAdmissibility(G, X, Y, Z = [], covariates = [])
        Tests whether a given list of covariates is admissible or not.
    """

    @staticmethod
    def FindFDSet(G, X, Y, I=[], R=[]):
        """
        Returns an admissible set, if any.

        Parameters
        ----------
        G : Graph
            A Graph object.
        X : Node | List[Node]
            A list of treatment variables.
        Y : Node | List[Node]
            A list of outcome variables.
        I,R : Node | List[Node]
            Variables that put constraints: I \subseteq Z \subseteq R.

        Returns
        -------
        admissible set: Node | None

        Raises
        ------
        AdjustmentSetsError
            An exception including an error message (and witness if any).
        """

        try:
            if not G or not X or not Y:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            # check if I or R includes X or Y
            if len(su.intersection(I, X, 'name')) > 0:
                raise AdjustmentSetsError(errors['treatmentInI'])
            if len(su.intersection(I, Y, 'name')) > 0:
                raise AdjustmentSetsError(errors['outcomeInI'])
            if len(su.intersection(R, X, 'name')) > 0:
                raise AdjustmentSetsError(errors['treatmentInR'])
            if len(su.intersection(R, Y, 'name')) > 0:
                raise AdjustmentSetsError(errors['outcomeInR'])

            # check if I is in R
            if not (su.isSubset(I, R, 'name') or su.equals(I, R, 'name')):
                raise AdjustmentSetsError(errors['IinR'])

            # start = time.time()
            R1 = FrontdoorAdjustment.GetCand2ndFDC(G, X, I, R)
            # end = time.time()
            # print(end - start)

            if R1 is None:
                return None

            # start = time.time()
            R2 = FrontdoorAdjustment.GetCand3rdFDC(G, X, Y, I, R1)
            # end = time.time()
            # print(end - start)

            if R2 is None:
                return None

            Z = R2
            CPG = FrontdoorAdjustment.GetCausalPathGraph(G, X, Y)

            # if DSeparation.test(CPG, X, Y, Z) == True:
            if TestSep(CPG, X, Y, Z) == True:
                return Z
            else:
                return None
        except AdjustmentSetsError as error:
            return {'error': error.__repr__()}
        except:
            return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    @staticmethod
    def GetCand2ndFDC(G, X, I=[], R=[]):
        R1 = R.copy()
        GXbar = gu.transform(G, None, X)

        for v in R:
            # if DSeparation.test(GXbar, X, [v], []) == False:
            if TestSep(GXbar, X, [v], []) == False:
                if su.belongs(v, I, compareNames):
                    return None
                else:
                    R1.remove(v)

        return R1

    @staticmethod
    def GetCand3rdFDC(G, X, Y, I=[], R1=[]):
        R2 = R1.copy()

        for v in R1:
            if FrontdoorAdjustment.GetDep(G, X, Y, [v], R1) == None:
                if su.belongs(v, I, compareNames):
                    return None
                else:
                    R2.remove(v)

        return R2

    @staticmethod
    def GetDep(G, X, Y, T=[], R1=[]):
        An = gu.ancestors(su.union(T, su.union(X, Y, 'name'), 'name'), G)
        Gprime = gu.subgraph(G, An)
        Gprime = ProjectionUtils.unproject(Gprime)
        GTbar = gu.transform(Gprime, None, T)
        Gprev = GTbar
        M = gu.moralize(GTbar)
        M.deleteNodes(X)

        Zprime = []
        Q = T.copy()
        visited = {}

        for t in T:
            visited[t['name']] = True

        while len(Q) > 0:
            u = Q.pop()

            if su.belongs(u, Y, compareNames):
                return None

            NR = su.intersection(
                FrontdoorAdjustment.GetNeighbors(u, M), R1, 'name')
            NR = list(filter(lambda n: n['name'] not in visited, NR))

            GTbar = gu.transform(Gprime, None, su.union(
                T, su.union(Zprime, NR, 'name'), 'name'))

            # M = gu.moralize(GTbar)
            # M.deleteNodes(X)

            # optimization: re-moralize w/o going through the entire moralization process
            directedEdgesToRemove = gu.getOutgoing(NR, Gprev)
            M = gu.remoralize(Gprev, GTbar, M, directedEdgesToRemove)
            Gprev = GTbar

            Nprime = FrontdoorAdjustment.GetNeighbors(u, M)
            Nprime = list(filter(lambda n: n['name'] not in visited, Nprime))
            NRprime = list(filter(lambda n: len(gu.getIncoming(n, G)) > 0, NR))

            N = su.union(Nprime, NRprime, 'name')

            Zprime = su.union(Zprime, NR, 'name')

            Q = su.union(Q, N, 'name')

            for n in N:
                visited[n['name']] = True

        return Zprime

    @staticmethod
    def GetNeighbors(v, G):
        adjacent = G.neighbors(v)
        N = list(filter(lambda n: n['type_'] == basicNodeType.id_, adjacent))
        L = list(filter(lambda n: n['type_'] == latentNodeType.id_, adjacent))
        Q = L.copy()

        visited = {}
        for n in N:
            visited[n['name']] = True
        for n in L:
            visited[n['name']] = True

        while len(Q) > 0:
            u = Q.pop()

            adjacent = G.neighbors(u)
            adjacent = list(
                filter(lambda n: n['name'] not in visited, adjacent))

            O = list(filter(lambda n: n['type_'] ==
                     basicNodeType.id_, adjacent))
            N = su.union(N, O, 'name')

            for n in O:
                visited[n['name']] = True

            L = list(filter(lambda n: n['type_'] ==
                     latentNodeType.id_, adjacent))

            Q = su.union(Q, L, 'name')

            for n in L:
                visited[n['name']] = True

        return N

    @staticmethod
    def GetCausalPathGraph(G, X, Y):
        nodes = su.union(X, su.union(Y, gu.pcp(G, X, Y), 'name'), 'name')
        Gsub = gu.subgraph(G, nodes)
        Gprime = gu.transform(Gsub, X, Y)
        bidirectedEdges = list(
            filter(lambda e: e['type_'] == bidirectedEdgeType.id_, Gprime.edges))
        Gprime.deleteEdges(bidirectedEdges)

        return Gprime

    @staticmethod
    def ListFDSets(G, X, Y, I=[], R=[], limit=1e8):
        """
        Returns a list of admissible sets.

        Parameters
        ----------
        G : Graph
            A Graph object.
        X : Node | List[Node]
            A list of treatment variables.
        Y : Node | List[Node]
            A list of outcome variables.
        I,R : Node | List[Node]
            Variables that put constraints: I \subseteq Z \subseteq R.
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

        try:
            if not G or not X or not Y:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            admissibleSets = []

            FrontdoorAdjustment.__ListFDSets(
                G, X, Y, I, R, admissibleSets, limit)

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
    def __ListFDSets(G, X, Y, I, R, admissibleSets, limit=1e8):
        if len(admissibleSets) >= limit:
            return

        if FrontdoorAdjustment.FindFDSet(G, X, Y, I, R) is not None:
            if su.equals(I, R, 'name'):
                admissibleSets.append(I)

                Inames = list(map(lambda n: n['name'], I))
                print(writeNodeNames(Inames))
            else:
                RminusI = su.difference(R, I, 'name')
                v = RminusI[0]

                FrontdoorAdjustment.__ListFDSets(G, X, Y, su.union(
                    I, [v], 'name'), R, admissibleSets, limit)
                FrontdoorAdjustment.__ListFDSets(
                    G, X, Y, I, su.difference(R, [v], 'name'), admissibleSets, limit)

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

    # @staticmethod
    # def testAdmissibility(graph, X, Y, Z=[], covariates=[]):
    #     """
    #     Tests whether a given list of covariates is admissible or not.

    #     Parameters
    #     ----------
    #     graph : Graph
    #         A Graph object.
    #     X : Node | List[Node]
    #         A list of treatment variables.
    #     Y : Node | List[Node]
    #         A list of outcome variables.
    #     Z : Node | List[Node]
    #         A list of adjusted variables (default is empty).
    #     covariates : Node | List[Node]
    #         A list of covariates (default is empty).

    #     Returns
    #     -------
    #     result: dict

    #     Raises
    #     ------
    #     AdjustmentSetsError
    #         An exception including an error message (and witness if any).
    #     """

    #     try:
    #         if not graph or not X or not Y:
    #             raise

    #         X = ou.makeArray(X)
    #         Y = ou.makeArray(Y)
    #         Z = ou.makeArray(Z)
    #         covariates = ou.makeArray(covariates)

    #         if len(X) == 0 and len(Y) == 0:
    #             raise AdjustmentSetsError(errors['treatmentAndOutcome'])
    #         elif len(X) == 0 and len(Y) != 0:
    #             raise AdjustmentSetsError(errors['treatment'])
    #         elif len(X) != 0 and len(Y) == 0:
    #             raise AdjustmentSetsError(errors['outcome'])

    #         result = {
    #             'admissible': BackdoorAdjustment.isAdmissible(graph, X, Y, Z, covariates),
    #             'conditions': BackdoorAdjustment.getAdmissibilityConditions(graph, X, Y, Z, covariates),
    #             'covariates': covariates
    #         }

    #         # return result
    #     except AdjustmentSetsError as error:
    #         return {'error': error.__repr__()}
    #     except:
    #         return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    # @staticmethod
    # def isAdmissible(G, X, Y, Z, covariates=[]):
    #     if not G or not X or not Y:
    #         return False

    #     if len(X) == 0 or len(Y) == 0:
    #         return False

    #     Gpbd = gu.gpbd(G, X, Y)

    #     adjusted = Z + covariates
    #     includesDescX = len(su.intersection(
    #         gu.descendants(X, G), adjusted, 'name')) > 0

    #     if includesDescX:
    #         return False

    #     return DSeparation.test(Gpbd, X, Y, adjusted)

    # @staticmethod
    # def getAdmissibilityConditions(G, X, Y, Z, covariates=[]):
    #     result = [
    #         {'satisfied': False, 'witness': []},
    #         {'satisfied': False, 'witness': []}
    #     ]

    #     if not G or not X or not Y or len(X) == 0 or len(Y) == 0:
    #         return result

    #     adjusted = Z + covariates
    #     DeX = gu.descendants(X, G)
    #     ZinDeX = []

    #     for z in adjusted:
    #         if su.belongs(z, DeX, compareNames):
    #             ZinDeX.append(z)

    #     condition1 = len(ZinDeX) == 0
    #     result[0]['satisfied'] = condition1

    #     if not condition1:
    #         result[0]['witness'] = ZinDeX

    #     condition2Paths = PathUtils.findConfoundingPaths(G, X, Y, adjusted)
    #     condition2 = len(condition2Paths) == 0
    #     result[1]['satisfied'] = condition2

    #     if not condition2:
    #         result[1]['witness'] = (G, condition2Paths, adjusted)

    #     return result
