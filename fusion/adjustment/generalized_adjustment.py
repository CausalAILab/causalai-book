from src.graph.classes.graph import Graph
# from src.graph.classes.graph_defs import basicNodeType, latentNodeType, undirectedEdgeType
from src.adjustment.backdoor_adjustment import BackdoorAdjustment
from src.adjustment.adjustment_sets_utils import getSelectionBiasNode, getViolatingPathEntries, writeNodeNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.common.object_utils import ObjectUtils as ou
from src.path_analysis.d_separation import DSeparation

from src.error.error_messages import defaultErrorMessage
from src.adjustment.classes.exceptions import AdjustmentSetsError

errors = {
    'treatment': 'Please specify the treatment variable(s).',
    'outcome': 'Please specify the outcome variable(s).',
    'treatmentAndOutcome': 'Please specify the treatment & outcome variables.'
}


class GeneralizedAdjustment():

    @staticmethod
    # Graph, Node[], Node[], number
    # Node[][][]
    def listAdmissibleSets(graph, X, Y, limit=1e8):
        try:
            if not graph or not X or not Y:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            S = getSelectionBiasNode(graph)

            # try listing backdoor-admissible sets if S node doesn't exist
            if S is None:
                return BackdoorAdjustment.listAdmissibleSets(graph, X, Y)

            XY = su.union(X, Y, 'name')
            V = gu.filterBasicNodes(graph.nodes)
            VS = su.union(V, [S], 'name')
            Dpcp = gu.Dpcp(graph, X, Y)
            R = su.difference(VS, su.union(XY, Dpcp, 'name'), 'name')
            T = su.difference(V, XY, 'name')
            Gpbd = gu.gpbd(graph, X, Y)

            admissibleSets = []

            GeneralizedAdjustment.listSepAB(
                Gpbd, X, Y, S, [S], R, T, admissibleSets, limit)

            #   remove sets which are not minimum-size
            minSize = float('inf')

            for pair in admissibleSets:
                Z = pair[0]

                if len(Z) < minSize:
                    minSize = len(Z)

            admissibleSets = [
                pair for pair in admissibleSets if len(pair[0]) == minSize]

            #   convert nodes to node names
            sets = []

            for pair in admissibleSets:
                newZ = list(map(lambda n: n['name'], pair[0]))
                newZT = list(map(lambda n: n['name'], pair[1]))
                newZ.sort()
                newZT.sort()

                newPair = (newZ, newZT)

                sets.append(newPair)

            # // sort sets
            # admissibleSets.sort((pair1, pair2) => {
            #     let Z1: Node[] = pair1[0];
            #     let Z2: Node[] = pair2[0];

            #     for (let i = 0; i < Z1.length; i++) {
            #         let z1: Node = Z1[i];
            #         let z2: Node = Z2[i];

            #         return sortByName(z1, z2);
            #     }
            # });

            return sets
        except AdjustmentSetsError as error:
            return {'error': error.__repr__()}
        except:
            return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    @staticmethod
    def listSepAB(G, X, Y, S, I, R, T, admissibleSets, limit=1e8):
        if len(admissibleSets) >= limit:
            return

        if GeneralizedAdjustment.existsSep(G, X, Y, I, R) and GeneralizedAdjustment.existsSep(G, [S], Y, [], su.intersection(R, T, 'name')):
            if su.equals(I, R, 'name'):
                GeneralizedAdjustment.listSepC(G, S, Y, [], su.intersection(
                    I, T, 'name'), su.difference(I, [S], 'name'), admissibleSets, limit)
            else:
                RminusI = su.difference(R, I, 'name')
                v = RminusI[0]

                GeneralizedAdjustment.listSepAB(G, X, Y, S, su.union(
                    I, [v], 'name'), R, T, admissibleSets, limit)
                GeneralizedAdjustment.listSepAB(G, X, Y, S, I, su.difference(
                    R, [v], 'name'), T, admissibleSets, limit)

    @staticmethod
    def listSepC(G, S, Y, I, R, Z, admissibleSets, limit=1e8):
        if len(admissibleSets) >= limit:
            return

        if GeneralizedAdjustment.existsSep(G, [S], Y, I, R):
            if su.equals(I, R, 'name'):
                sortedZ = sorted(Z, key=lambda n: n['name'])
                sortedI = sorted(I, key=lambda n: n['name'])
                pair = (sortedZ, sortedI)

                admissibleSets.append(pair)
            else:
                RminusI = su.difference(R, I, 'name')
                v = RminusI[0]

                GeneralizedAdjustment.listSepC(G, S, Y, su.union(
                    I, [v], 'name'), R, Z, admissibleSets, limit)
                GeneralizedAdjustment.listSepC(G, S, Y, I, su.difference(
                    R, [v], 'name'), Z, admissibleSets, limit)

    @staticmethod
    def existsSep(G, X, Y, I, R):
        XYI = su.union(su.union(X, Y, 'name'), I, 'name')
        AnXYI = gu.ancestors(XYI, G)
        AnXYI = su.union(AnXYI, XYI, 'name')
        Zprime = su.intersection(AnXYI, R, 'name')

        return DSeparation.test(G, X, Y, Zprime)

    @staticmethod
    def printAdmissibleSets(result):
        if result is None:
            return

        if len(result) == 0:
            print('No generalized adjustment pairs.')
            return

        txt = str(len(result)) + ' generalized adjustment pair' + \
            ('s' if len(result) > 1 else '') + ' (biased / unbiased):'
        print(txt)

        for pair in result:
            line = writeNodeNames(pair[0]) + ' / ' + writeNodeNames(pair[1])

            print(line)

    # Graph, Node[], Node[], Node[], Node[]

    @staticmethod
    def testAdmissibility(G, X, Y, covariates, externalData=[]):
        try:
            if not G or not X or not Y or not covariates:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)
            covariates = ou.makeArray(covariates)
            externalData = ou.makeArray(externalData)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            S = getSelectionBiasNode(G)

            if S is None:
                raise

            result = {
                'admissible': GeneralizedAdjustment.isGeneralizedAdmissible(G, X, Y, covariates, externalData),
                'conditions': GeneralizedAdjustment.getGeneralizedAdmissibilityConditions(G, X, Y, covariates, externalData),
                'covariates': covariates,
                'externalData': externalData
            }

            return result
        except AdjustmentSetsError as error:
            return {'error': error.__repr__()}
        except:
            return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    @staticmethod
    def isGeneralizedAdmissible(G, X, Y, covariates, externalData=[]):
        if not G or not X or not Y or not covariates:
            return False

        if len(X) == 0 or len(Y) == 0:
            return False

        S = getSelectionBiasNode(G)

        if S is None:
            return False

        # condition 1: no nodes in Z is a descendant in G_bar_X of any node (!= X) lying on proper causal path from X to Y
        GbarX = gu.transform(G, X, None)
        Dpcp = gu.Dpcp(GbarX, X, Y)

        condition1 = len(su.intersection(Dpcp, covariates, 'name')) == 0

        if not condition1:
            return False

        # condition 2: X \indep Y | Z,S in G_pbd(X,Y)
        Gpbd = gu.gpbd(G, X, Y)

        condition2 = DSeparation.test(
            Gpbd, X, Y, su.union(covariates, [S], 'name'))

        if not condition2:
            return False

        # condition 3: Y \indep S | Z^T in G_pbd(X,Y)
        condition3 = DSeparation.test(Gpbd, Y, S, externalData)

        if not condition3:
            return False

        return True

    @staticmethod
    def getGeneralizedAdmissibilityConditions(G, X, Y, covariates, externalData=[]):
        result = [
            {'satisfied': False, 'witness': []},
            {'satisfied': False, 'witness': [], 'metadata': {'ZS': []}},
            {'satisfied': False, 'witness': []}
        ]

        if not G or not X or not Y or not covariates:
            return result

        if len(X) == 0 or len(Y) == 0:
            return result

        # condition 1: no nodes in Z is a descendant in G_bar_X of any node (!= X) lying on proper causal path from X to Y
        GbarX = gu.transform(G, X, None)
        Dpcp = gu.Dpcp(GbarX, X, Y)

        condition1 = len(su.intersection(Dpcp, covariates, 'name')) == 0
        result[0]['satisfied'] = condition1

        if not condition1:
            violatingZ = su.difference(covariates, Dpcp, 'name')

            result[0]['witness'] = violatingZ

        # condition 2: X \indep Y | Z,S in G_pbd(X,Y)
        Gpbd = gu.gpbd(G, X, Y)
        S = getSelectionBiasNode(G)
        ZS = su.union(covariates, [S], 'name')

        result[1]['metadata']['ZS'] = ZS

        condition2Paths = DSeparation.findDConnectedPaths(Gpbd, X, Y, ZS)

        condition2 = len(condition2Paths) == 0
        result[1]['satisfied'] = condition2

        if not condition2:
            result[1]['witness'] = getViolatingPathEntries(
                Gpbd, condition2Paths, ZS)

        # condition 3: Y \indep S | Z^T in G_pbd(X,Y)
        condition3Paths = DSeparation.findDConnectedPaths(
            Gpbd, Y, [S], externalData)

        condition3 = len(condition3Paths) == 0
        result[2]['satisfied'] = condition3

        if not condition3:
            result[2]['witness'] = getViolatingPathEntries(
                Gpbd, condition3Paths, externalData)

        return result
