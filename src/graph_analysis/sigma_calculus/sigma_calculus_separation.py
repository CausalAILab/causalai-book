from src.graph_analysis.classes.transform_nodes import TransformNodes
from src.graph_analysis.sigma_calculus.classes.sigma_calculus_separation_result import SigmaCalculusSeparationResult

from src.inference.utils.graph_utils import GraphUtils as gu
from src.common.object_utils import ObjectUtils as ou
from src.path_analysis.d_separation import DSeparation
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.graph_analysis.sigma_calculus.sigma_calculus_utils import SigmaCalculusUtils


class SigmaCalculusSeparation():

    # Graph, Node | Node[], Node | Node[], Node | Node[], TransformNodes, Intervention[]
    # SigmaCalculusSeparationResult
    def test(self, G, X, Y, Z = None, tx = None, intvs = []):
        if not G or not X or not Y:
            return None
        
        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        if tx is None:
            tx = TransformNodes()

        txGraph = gu.transform(G, tx.over, tx.under)
        graphSigma = SigmaCalculusUtils.createGraphSigma(txGraph, intvs)
        
        paths = DSeparation.findDConnectedPaths(graphSigma, X, Y, Z)
        
        result = SigmaCalculusSeparationResult()
        result.separable = len(paths) == 0
        result.paths = paths

        return result


    def printResult(self, query, Tx, intvs, result):
        if query is None or Tx is None or intvs is None or result is None:
            return

        X = query.P.Z
        Y = query.P.Y
        Z = query.P.W

        # add sigma to G
        # grab intv nodes
        nodes = []

        for intv in intvs:
            nodes.append(intv.target)

        sigmaExp = self.createSigmaExpression(nodes)
        TxExp = None

        if len(Tx.over) > 0 and len(Tx.under) > 0:
            TxExp = eu.create('concat', ['G_{\\overline{', eu.write(Tx.over), '} \\underline{' + eu.write(Tx.under) + '}}'])
        elif len(Tx.over) > 0 and len(Tx.under) == 0:
            TxExp = eu.create('concat', ['G_{\\overline{', eu.write(Tx.over), '}}'])
        elif len(Tx.over) == 0 and len(Tx.under) > 0:
            TxExp = eu.create('concat', ['G_{\\underline{', eu.write(Tx.under), '}}'])

        GExp = eu.create('concat', ['G_{', sigmaExp, TxExp, '}'])
        exp = eu.create('indep', [Y, X, Z, GExp])

        indepLine = eu.write(exp) + ': ' + str(result.separable)

        print(indepLine)

        # print paths


    def createSigmaExpression(self, nodes):
        if not nodes:
            return None

        parts = []

        for node in nodes:
            part = eu.create('coef', ['sigma', node])
            parts.append(part)

        return eu.create('concat', parts)