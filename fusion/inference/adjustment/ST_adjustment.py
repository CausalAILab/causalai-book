from src.adjustment.st_adjustment import STAdjustment as ST
from src.transportability.classes.transportability import targetPopulation
 
from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.compute.compute_utils import ComputeUtils as cu
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.common.object_utils import ObjectUtils as ou


STAdjustmentName = 'ST adjustment'

class STAdjustment():

    @staticmethod
    def findAdjustment(G, X, Y, W, sourcePopulation):
        if not G or not X or not Y or not W or not sourcePopulation:
            return None

        sets = ST.listAdmissibleSets(G, X, Y, W, sourcePopulation, 1)

        if not sets or len(sets) == 0:
            return None
        
        # convert node names to nodes
        admNodes = []

        if sets is not None:
            for adm in sets:
                nodes = gu.getNodesByName(adm, G)
                admNodes.append(nodes)
        
        # find a pair that uses external data
        Z = admNodes[0]
        S = cu.getSelectionBiasNode(G)

        expression = None
        firstTerm = None
        SExp = eu.create('=', [S, '1'])

        if S is not None:
            if su.isEmpty(Z):
                firstTerm = eu.create('prob', [Y, SExp, X, sourcePopulation.label])
            else:
                firstTerm = eu.create('prob', [Y, eu.create('list', [Z, SExp]), X, sourcePopulation.label])
        else:
            firstTerm = eu.create('prob', [Y, Z, X, sourcePopulation.label])

        if su.isEmpty(Z):
            expression = firstTerm
        else:
            expression = eu.create('sum', [Z, None, eu.create('product', [
                firstTerm,
                eu.create('prob', [Z, None, None, targetPopulation.label])
            ])])

        return {
            'name': 'st-adjustment',
            'covariates': Z,
            'expression': expression
        }