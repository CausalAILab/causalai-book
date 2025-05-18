from src.graph_analysis.classes.transform_nodes import TransformNodes
from src.graph_analysis.do_calculus.classes.do_calculus_separation_result import DoCalculusSeparationResult

from src.inference.utils.graph_utils import GraphUtils as gu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.path_analysis.d_separation import DSeparation


class DoCalculusSeparation():

    # Graph, Node | Node[], Node | Node[], Node | Node[], TransformNodes
    # DoCalculusSeparationResult
    def test(self, G, X, Y, Z = None, tx = None):
        if not G or not X or not Y:
            return None
        
        X = ou.makeArray(X)
        Y = ou.makeArray(Y)
        Z = ou.makeArray(Z)

        if tx is None:
            tx = TransformNodes()

        txGraph = gu.transform(G, tx.over, tx.under)

        paths = DSeparation.findDConnectedPaths(txGraph, X, Y, Z)

        result = DoCalculusSeparationResult()
        result.separable = len(paths) == 0
        result.paths = paths

        return result


    def printResult(self, query, Tx, result):
        if query is None or Tx is None or result is None:
            return

        X = query.P.Z
        Y = query.P.Y
        Z = query.P.W

        TxExp = None

        if len(Tx.over) > 0 and len(Tx.under) > 0:
            TxExp = eu.create('concat', ['G_{\\overline{', eu.write(Tx.over), '} \\underline{' + eu.write(Tx.under) + '}}'])
        elif len(Tx.over) > 0 and len(Tx.under) == 0:
            TxExp = eu.create('concat', ['G_{\\overline{', eu.write(Tx.over), '}}'])
        elif len(Tx.over) == 0 and len(Tx.under) > 0:
            TxExp = eu.create('concat', ['G_{\\underline{', eu.write(Tx.under), '}}'])

        exp = eu.create('indep', [Y, X, Z, TxExp])

        indepLine = eu.write(exp) + ': ' + str(result.separable)

        print(indepLine)

        # print paths