import itertools

# from src.graph.classes.graph import Graph
# from src.graph.classes.graph_defs import basicNodeType, latentNodeType, undirectedEdgeType
from src.adjustment.adjustment_sets_utils import getSelectionBiasNode, getSelectionNodes, getViolatingPathEntries, writeNodeNames
from src.adjustment.backdoor_adjustment import BackdoorAdjustment
from src.inference.utils.graph_utils import compareNames

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


class STAdjustment():

    # Graph, Node[], Node[], Node[], Population, number
    # Node[][]
    @staticmethod
    def listAdmissibleSets(G, X, Y, W, sourcePopulation, limit=1e8):
        try:
            if not G or not X or not Y or not W or not sourcePopulation:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)
            W = ou.makeArray(W)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            T = getSelectionNodes(G)
            S = getSelectionBiasNode(G)

            T = list(filter(
                lambda n: 'metadata' in n and 'populations' in n['metadata'] and sourcePopulation.label in n['metadata']['populations'], T))

            # try listing backdoor-admissible sets if T and S don't exist
            if len(T) == 0 and S is None:
                return BackdoorAdjustment.listAdmissibleSets(G, X, Y)

            F = gu.Dpcp(G, X, Y)
            R = su.difference(W, su.union(
                su.union(X, Y, 'name'), F, 'name'), 'name')

            admissibleSets = []

            STAdjustment.listGAdjIR(
                G, X, Y, T, S, [], R, admissibleSets, limit)

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
    def listGAdjIR(G, X, Y, T, S, I, R, admissibleSets, limit=1e8):
        if len(admissibleSets) >= limit:
            return

        GbarX = gu.transform(G, X, None)

        if STAdjustment.existsSep(GbarX, su.union(T, [S] if S is not None else [], 'name'), Y, I, R):
            if su.equals(I, R, 'name'):
                sortedI = sorted(I, key=lambda n: n['name'])

                admissibleSets.append(sortedI)
            else:
                A = None
                DeX = su.union(gu.descendants(X, G), X, 'name')
                RminusI = su.difference(R, I, 'name')

                for node in RminusI:
                    if not su.belongs(node, DeX, compareNames):
                        A = node
                        break

                if A is None:
                    for node in RminusI:
                        if DSeparation.test(GbarX, node, Y, su.union(I, X, 'name')):
                            A = node
                            break

                    if A is None:
                        for node in RminusI:
                            if STAdjustment.isEAdmissible(G, X, Y, su.union(I, [node], 'name')):
                                A = node
                                break

                if A is not None:
                    STAdjustment.listGAdjIR(G, X, Y, T, S, su.union(
                        I, [A], 'name'), R, admissibleSets, limit)
                    STAdjustment.listGAdjIR(G, X, Y, T, S, I, su.difference(
                        R, [A], 'name'), admissibleSets, limit)
                else:
                    STAdjustment.listGAdjIR(
                        G, X, Y, T, S, I, I, admissibleSets, limit)

    @staticmethod
    def isEAdmissible(G, X, Y, Z):
        if not G or not X or not Y or not Z:
            return False

        DeX = su.union(gu.descendants(X, G), X, 'name')
        Zd = su.intersection(Z, DeX, 'name')

        if len(Zd) == 0:
            return True

        GbarX = gu.transform(G, X, None)

        for z in Zd:
            Zminus = su.difference(Z, [z], 'name')
            AnZminus = gu.ancestors(Zminus, G)
            XZ = su.difference(X, AnZminus, 'name')
            GbarXZ = gu.transform(G, XZ, None)

            cond1 = DSeparation.test(GbarX, z, Y, su.union(Zminus, X, 'name'))
            cond2 = DSeparation.test(GbarXZ, z, X, Zminus)

            if cond1 or cond2:
                return STAdjustment.isEAdmissible(G, X, Y, Zminus)

        return False

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
            print('No ST adjustment sets.')
            return

        txt = '' + str(len(result)) + ' ST adjustment set' + \
            ('s' if len(result) > 1 else '') + ':'
        print(txt)

        for adm in result:
            print(writeNodeNames(adm))

    # Graph, Node[], Node[], Node[], Node[], Population

    @staticmethod
    def testAdmissibility(G, X, Y, covariates, observations, sourcePopulation):
        try:
            if not G or not X or not Y:
                raise

            if not sourcePopulation:
                raise

            X = ou.makeArray(X)
            Y = ou.makeArray(Y)
            covariates = ou.makeArray(covariates)
            observations = ou.makeArray(observations)

            if len(X) == 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['treatmentAndOutcome'])
            elif len(X) == 0 and len(Y) != 0:
                raise AdjustmentSetsError(errors['treatment'])
            elif len(X) != 0 and len(Y) == 0:
                raise AdjustmentSetsError(errors['outcome'])

            # covariates is not a subset of observations
            if not su.isSubset(covariates, observations, 'name'):
                remaining = su.difference(covariates, observations, 'name')

                raise

            S = getSelectionBiasNode(G)

            if S is None:
                raise

            result = {
                'admissible': STAdjustment.isSTAdmissible(G, X, Y, covariates, observations),
                'conditions': STAdjustment.getSTAdmissibilityConditions(G, X, Y, covariates, observations),
                'covariates': covariates,
                'observations': observations
            }

            return result
        except AdjustmentSetsError as error:
            return {'error': error.__repr__()}
        except:
            return {'error': AdjustmentSetsError(defaultErrorMessage).__repr__()}

    @staticmethod
    def isSTAdmissible(G, X, Y, covariates, observations):
        if not G or not X or not Y or not covariates:
            return False

        if len(X) == 0 or len(Y) == 0:
            return False

        # covariates shoulbe be a subset of observations
        if not su.isSubset(covariates, observations, 'name'):
            return False

        GbarX = gu.transform(G, X, None)
        DeX = gu.descendants(X, G)
        Znd = su.difference(covariates, DeX, 'name')
        Zd = su.intersection(covariates, DeX, 'name')
        Zp = []

        # Zp = z in Zd where z not \indep Y | Znd,X in G_bar_X
        for z in Zd:
            if not DSeparation.test(GbarX, z, Y, su.union(Znd, X, 'name')):
                Zp.append(z)

        # condition 1: Zp \indep X | (Z - Zp)
        ZminusZp = su.difference(covariates, Zp, 'name')

        condition1 = DSeparation.test(G, Zp, X, ZminusZp)

        if not condition1:
            return False

        # condition 2: Y \indep S,T | Z,X in G_bar_X
        T = getSelectionNodes(G)
        S = getSelectionBiasNode(G)
        ST = T.copy()

        if S is not None:
            ST = su.union([S], ST, 'name')

        ZX = su.union(covariates, X, 'name')

        condition2 = DSeparation.test(GbarX, Y, ST, ZX)

        if not condition2:
            return False

        return True

    @staticmethod
    def getSTAdmissibilityConditions(G, X, Y, covariates, observations):
        result = [
            {'satisfied': False, 'witness': [],
                'metadata': {'ZP': [], 'ZminusZp': []}},
            {'satisfied': False, 'witness': [], 'metadata': {'ST': [], 'ZX': []}}
        ]

        if not X or not Y or len(X) == 0 or len(Y) == 0:
            return result

        if not su.isSubset(covariates, observations, 'name'):
            return result

        GbarX = gu.transform(G, X, None)
        DeX = gu.descendants(X, G)
        Znd = su.difference(covariates, DeX, 'name')
        Zd = su.intersection(covariates, DeX, 'name')
        Zp = []

        # Zp = z in Zd where z not \indep Y | Znd,X in G_bar_X
        for z in Zd:
            if not DSeparation.test(GbarX, z, Y, su.union(Znd, X, 'name')):
                Zp.append(z)

        # condition 1: Zp \indep X | (Z - Zp)
        ZminusZp = su.difference(covariates, Zp, 'name')

        result[0]['metadata']['Zp'] = Zp
        result[0]['metadata']['ZminusZp'] = ZminusZp

        condition1Paths = DSeparation.findDConnectedPaths(G, Zp, X, ZminusZp)
        condition1 = len(condition1Paths) == 0
        result[0]['satisfied'] = condition1

        if not condition1:
            result[0]['witness'] = getViolatingPathEntries(
                G, condition1Paths, ZminusZp)

        # condition 2: Y \indep S,T | Z,X in G_bar_X
        T = getSelectionNodes(G)
        S = getSelectionBiasNode(G)
        ST = T.copy()

        if S is not None:
            ST = su.union([S], ST, 'name')

        ZX = su.union(covariates, X, 'name')

        result[1]['metadata']['ST'] = ST
        result[1]['metadata']['ZX'] = ZX

        condition2Paths = DSeparation.findDConnectedPaths(GbarX, Y, ST, ZX)
        condition2 = len(condition2Paths) == 0
        result[1]['satisfied'] = condition2

        if not condition2:
            result[1]['witness'] = getViolatingPathEntries(
                GbarX, condition2Paths, ZX)

        return result
