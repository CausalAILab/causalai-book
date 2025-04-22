from src.graph_analysis.do_calculus.classes.do_calculus_inspection_result import DoCalculusInspectionResult
from src.graph_analysis.classes.transform_nodes import TransformNodes
from src.path_analysis.d_separation import DSeparation

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.inference.utils.expression_utils import ExpressionUtils as eu

Zstr = '\\zeta'
Wstr = '\\psi'

class DoCalculusInspector():

    # DoCalculusInspectionQuery, Graph
    # DoCalculusInspectionResult
    def test(self, query, graph, return_graph = False):

        if not query or not graph:
            return None

        if query.rule not in [1,2,3]:
            return None

        if not query.P or not query.P.Y or not query.P.Z:
            return None

        # validateDisjointVariables

        rule = query.rule
        P = query.P

        result = DoCalculusInspectionResult()

        transformedGraph = None
        XW = su.union(P.X, P.W, 'name')

        if rule == 1:
            # delete observations
            # Z is observed
            # remove Z from W in inference
            transformedGraph = gu.transform(graph, P.X, None)
            result.transformation.over = P.X

            result.applicable = DSeparation.test(transformedGraph, P.Y, P.Z, XW)
            result.expression = eu.create('prob', [P.Y, su.union(P.Z, P.W, 'name'), P.X])
            result.inference = eu.create('prob', [P.Y, P.W, P.X])
            result.independence = self.createIndependenceExpression(query)

            if not result.applicable:
                result.violating_paths = DSeparation.findDConnectedPaths(transformedGraph, P.Y, P.Z, XW)
        elif rule == 2:
            # remove the do()
            # Z is interventional
            # remove Z from interventional and add to W
            transformedGraph = gu.transform(graph, P.X, P.Z)
            result.transformation.over = P.X
            result.transformation.under = P.Z

            result.applicable = DSeparation.test(transformedGraph, P.Y, P.Z, XW)
            result.expression = eu.create('prob', [P.Y, P.W, su.union(P.Z, P.X, 'name')])
            result.inference = eu.create('prob', [P.Y, su.union(P.Z, P.W, 'name'), P.X])
            result.independence = self.createIndependenceExpression(query)
            
            if not result.applicable:
                result.violating_paths = DSeparation.findDConnectedPaths(transformedGraph, P.Y, P.Z, XW)

        elif rule == 3:
            # delete the do()
            # Z is interventional
            # remove Z from interventional
            # handle Z(W): Z - An(W) in G_bar_X
            GbarX = gu.transform(graph, P.X, None)
            AnWInGbarX = gu.ancestors(P.W, GbarX)
            ZW = su.difference(P.Z, AnWInGbarX, 'name')
            nodesOver = su.union(ZW, P.X, 'name')

            transformedGraph = gu.transform(graph, nodesOver, None)
            result.transformation.over = nodesOver

            result.applicable = DSeparation.test(transformedGraph, P.Y, P.Z, XW)
            result.expression = eu.create('prob', [P.Y, P.W, su.union(P.Z, P.X, 'name')])
            result.inference = eu.create('prob', [P.Y, P.W, P.X])
            result.independence = self.createIndependenceExpression(query, graph)

            if not result.applicable:
                result.violating_paths = DSeparation.findDConnectedPaths(transformedGraph, P.Y, P.Z, XW)

        if return_graph:
            return result, transformedGraph
        
        return result

    
    def createIndependenceExpression(self, query, graph = None):
        tx = TransformNodes()
        XW = su.union(query.P.X, query.P.W, 'name')
        
        if query.rule == 1:
            tx.over = query.P.X

            return eu.create('indep', [query.P.Y, query.P.Z, XW, self.writeTransformedGraphExpression(tx, query.rule)])

        elif query.rule == 2:
            tx.over = query.P.X
            tx.under = query.P.Z
            
            return eu.create('indep', [query.P.Y, query.P.Z, XW, self.writeTransformedGraphExpression(tx, query.rule)])

        elif query.rule == 3:
            if not graph:
                return None

            GbarX = gu.transform(graph, query.P.X, None)
            AnWInGbarX = gu.ancestors(query.P.W, GbarX)
            ZW = su.difference(query.P.Z, AnWInGbarX, 'name')
            nodesOver = su.union(ZW, query.P.X, 'name')

            tx.over = nodesOver

            return eu.create('indep', [query.P.Y, query.P.Z, XW, self.writeTransformedGraphExpression(tx, query.rule)])


    # TransformNodes, number, any
    # Expression
    def writeTransformedGraphExpression(self, tx, rule):
        if not tx:
            return None

        if len(tx.over) > 0 and len(tx.under) > 0:
            return eu.create('concat', ['G_{\\overline{', eu.write(tx.over), '} \\underline{' + eu.write(tx.under) + '}}'])
        elif len(tx.over) > 0 and len(tx.under) == 0:
            return eu.create('concat', ['G_{\\overline{', eu.write(tx.over), '}}'])
        elif len(tx.over) == 0 and len(tx.under) > 0:
            return eu.create('concat', ['G_{\\underline{', eu.write(tx.under), '}}'])
        else:
            return None


    def printResult(self, query, result):
        if query is None or result is None:
            return

        line = 'Applicable: ' + str(result.applicable)
        print(line)

        line = 'Expression: ' + eu.write(result.expression)
        print(line)

        line = 'Evaluation: ' + eu.write(result.independence)
        print(line)
        
        if result.applicable:
            line = 'Result: ' + eu.write(eu.create('=', [result.expression, result.inference]))
        else:
            line = 'Result: ' + eu.write(eu.create('!=', [result.expression, result.inference]))
        print(line)