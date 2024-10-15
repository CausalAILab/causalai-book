from src.adjustment.generalized_adjustment import GeneralizedAdjustment as GA

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.compute.compute_utils import ComputeUtils as cu
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.common.object_utils import ObjectUtils as ou


GeneralizedAdjustmentName = 'Generalized adjustment'

class GeneralizedAdjustment():

    # /**
    #  * Finds a generalized adjustment expression for the effect P(y | do(x)) according to the given
    #  * parameters if one exists
    #  * @param G The graph
    #  * @param X Treatment variables
    #  * @param Y Outcome variables
    #  * @param W External data
    #  * @param P Probability expression
    #  * @returns An adjustment expression for P(y | do(x)) or null if none exists
    #  */
    @staticmethod
    def findAdjustment(G, X, Y, W, P):
        if not G or not X or not Y:
            return None

        W = ou.makeArray(W)

        sets = GA.listAdmissibleSets(G, X, Y)
        
        if not sets or len(sets) == 0:
            return None
        
        # convert node names to nodes
        admNodes = []

        if sets is not None:
            for pair in sets:
                cov = gu.getNodesByName(pair[0], G)
                ext = gu.getNodesByName(pair[1], G)
                admNodes.append((cov, ext))
        
        # find a pair that uses external data
        Z = None
        ZT = None

        for pair in admNodes:
            cov = pair[0]
            ext = pair[1]

            if su.equals(W, ext, 'name'):
                Z = cov
                ZT = ext
                break
        
        if Z is None or ZT is None:
            return None

        ZS = su.difference(Z, ZT, 'name')
        S = cu.getSelectionBiasNode(G)

        SExp = eu.create('=', [S, '1'])
        firstExp = eu.create('prob', [Y, eu.create('list', [X, SExp])]) if su.isEmpty(Z) else eu.create('prob', [Y, eu.create('list', [X, Z, SExp])])
        secondExp = None
        
        if not su.isEmpty(ZS):
            secondExp = eu.create('prob', [ZS, SExp]) if su.isEmpty(ZT) else eu.create('prob', [ZS, eu.create('list', [ZT, SExp])])

        thirdExp = None if su.isEmpty(ZT) else eu.create('prob', [ZT])

        expression = eu.create('sum', [Z, None, eu.create('product', [
            firstExp,
            secondExp,
            thirdExp
        ])])
        
        return {
            'name': GeneralizedAdjustmentName,
            'covariates': Z,
            'external': ZT,
            'expression': expression
        }