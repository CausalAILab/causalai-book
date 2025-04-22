from src.graph_analysis.sigma_calculus.classes.sigma_calculus_inspection_result import SigmaCalculusInspectionResult
from src.graph_analysis.classes.transform_nodes import TransformNodes
from src.path_analysis.d_separation import DSeparation
from src.intervention.classes.intervention import interventionNodeType
from src.intervention.classes.intervention_type import InterventionType

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.inference.utils.expression_utils import ExpressionUtils as eu


class SigmaCalculusInspector():

    # SigmaCalculusInspectionQuery, Graph
    # SigmaCalculusInspectionResult
    def test(self, query, graph):
        if not query or not graph:
            return None

        if query.rule not in [1,2,3]:
            return None

        if not query.P or not query.P.Y or not query.P.Z:
            return None

        # validateDisjointVariables

        rule = query.rule
        P = query.P

        sigmaX = query.interventions.X
        sigmaZ = query.interventions.Z
        sigmaZprime = query.interventions.Zprime

        result = SigmaCalculusInspectionResult()

        if rule == 1:
            # R1: add/remove obs. Z
            #     if (Y \indep Z | W) in G_sigma_X
            #     P(y | z, w; sigma_X) = P(y | w; sigma_X)
            Tx = self.getTransformNodes(rule, sigmaX, graph)
            # implement overExcept, underExcept
            GsigmaX = gu.transform(graph, Tx.over, Tx.under, Tx.overExcept, Tx.underExcept)
            
            result.transformation = Tx
            result.applicable = DSeparation.test(GsigmaX, P.Y, P.Z, P.W)
            result.expression = self.writeQueryExpression(query)
            result.inference = self.writeInferenceExpression(query)
            result.independence = self.writeIndependenceExpression(query)

            if not result.applicable:
                result.violatingPaths = DSeparation.findDConnectedPaths(GsigmaX, P.Y, P.Z, P.W)

        elif rule == 2:
            # R2: change sigma_Z w/ obs. Z
            #     P(y | z, w; sigma_X, sigma_Z) = P(y | z, w; sigma_X, sigma_Z')
            #         if (Y \indep Z | W) in G_sigma_X & sigma_Z & \underline(Z)
            #                              & G_sigma_X & sigma_Z' & \underline(Z)
            metadata = {'P': query.P}

            sigmaXZ = sigmaX + sigmaZ
            
            Tx = self.getTransformNodes(rule, sigmaXZ, graph, metadata)
            GsigmaXZ_Zbar = gu.transform(graph, Tx.over, Tx.under, Tx.overExcept, Tx.underExcept)

            sigmaXZprime = sigmaX + sigmaZprime
            newIntvsTx = self.getTransformNodes(rule, sigmaXZprime, graph, metadata)
            GsigmaXZprime_Zbar = gu.transform(graph, newIntvsTx.over, newIntvsTx.under, newIntvsTx.overExcept, newIntvsTx.underExcept)
            
            result.transformation = Tx
            result.applicable = DSeparation.test(GsigmaXZ_Zbar, P.Y, P.Z, P.W) and DSeparation.test(GsigmaXZprime_Zbar, P.Y, P.Z, P.W)
            result.expression = self.writeQueryExpression(query)
            result.inference = self.writeInferenceExpression(query)
            result.independence = self.writeIndependenceExpression(query)

            if not result.applicable:
                result.violating_paths = DSeparation.findDConnectedPaths(GsigmaXZ_Zbar, P.Y, P.Z, P.W) + DSeparation.findDConnectedPaths(GsigmaXZprime_Zbar, P.Y, P.Z, P.W)
                result.violating_paths = su.unique(result.violating_paths)

        elif rule == 3:
            # R3: change sigma_Z w/o obs. Z
            #     P(y | w; sigma_X, sigma_Z) = P(y | w; sigma_X, sigma_Z')
            #         if (Y \indep Z | W) in G_sigma_X & sigma_Z & \overline(Z(W))
            #                              & G_sigma_X & sigma_Z' & \overline(Z(W))
            metadata = {'P': query.P, 'sigmaX': sigmaX}

            sigmaXZ = sigmaX + sigmaZ
            Tx = self.getTransformNodes(rule, sigmaXZ, graph, metadata)
            GsigmaXZ_barZW = gu.transform(graph, Tx.over, Tx.under, Tx.overExcept, Tx.underExcept)
            
            sigmaXZprime = sigmaX + sigmaZprime
            newIntvsTx = self.getTransformNodes(rule, sigmaXZprime, graph, metadata)
            GsigmaXZprime_barZW = gu.transform(graph, newIntvsTx.over, newIntvsTx.under, newIntvsTx.overExcept, newIntvsTx.underExcept)

            result.transformation = Tx
            result.applicable = DSeparation.test(GsigmaXZ_barZW, P.Y, P.Z, P.W) and DSeparation.test(GsigmaXZprime_barZW, P.Y, P.Z, P.W)
            result.expression = self.writeQueryExpression(query)
            result.inference = self.writeInferenceExpression(query)
            result.independence = self.writeIndependenceExpression(query, graph, metadata)

            if not result.applicable:
                result.violating_paths = DSeparation.findDConnectedPaths(GsigmaXZ_barZW, P.Y, P.Z, P.W) + DSeparation.findDConnectedPaths(GsigmaXZprime_barZW, P.Y, P.Z, P.W)
                result.violating_paths = su.unique(result.violating_paths)

        return result

    
    # SigmaCalculusRuleQuery
    # Expression
    def writeQueryExpression(self, query):
        rule = query.rule
        P = query.P

        # P(y | t, w; sigma_X)
        if rule == 1:
            TW = su.union(P.Z, P.W, 'name')
            sigmaXExp = self.createSigmaExpression(P.X)

            # P(y | t, w; sigma_X)
            if len(P.X) > 0:
                return eu.create('prob', [P.Y, eu.create('concat', [TW, '; ', sigmaXExp])])

            # P(y | t, w)
            else:
                return eu.create('prob', [P.Y, TW])

        # P(y | z, w; sigma_X, sigma_Z)
        elif rule == 2:
            ZW = su.union(P.Z, P.W, 'name')
            sigmaXExp = self.createSigmaExpression(P.X)
            sigmaZExp = self.createSigmaExpression(P.Z)

            # P(y | z, w; sigma_X, sigma_Z)
            if len(P.X) > 0:
                sigmaExp = eu.create('concat', [sigmaXExp, sigmaZExp])

                return eu.create('prob', [P.Y, eu.create('concat', [ZW, '; ', sigmaExp])])

            # P(y | z, w; sigma_Z)
            else:
                return eu.create('prob', [P.Y, eu.create('concat', [ZW, '; ', sigmaZExp])])

        # P(y | w; sigma_X, sigma_Z)
        elif rule == 3:
            sigmaZExp = self.createSigmaExpression(P.Z)
            
            # P(y | w; sigma_X, sigma_Z)
            if len(P.X) > 0:
                sigmaXExp = self.createSigmaExpression(P.X)
                sigmaExp = eu.create('concat', [sigmaXExp, sigmaZExp])

                if len(P.W) > 0:
                    return eu.create('prob', [P.Y, eu.create('concat', [P.W, '; ', sigmaExp])])
                else:
                    return eu.create('prob', [P.Y, sigmaExp])

            # P(y | w; sigma_Z)
            else:
                if len(P.W) > 0:
                    return eu.create('prob', [P.Y, eu.create('concat', [P.W, '; ', sigmaZExp])])
                else:
                    return eu.create('prob', [P.Y, sigmaZExp])

        
    # SigmaCalculusRuleQuery
    # Expression
    def writeInferenceExpression(self, query):
        rule = query.rule
        P = query.P

        # P(y | w; sigma_X)
        if rule == 1:
            sigmaXExp = self.createSigmaExpression(P.X)

            if len(P.W) > 0:
                # P(y | w; sigma_X)
                if len(P.X) > 0:
                    return eu.create('prob', [P.Y, eu.create('concat', [P.W, '; ', sigmaXExp])])
                # P(y | w)
                else:
                    return eu.create('prob', [P.Y, P.W])
                
            else:
                # P(y | sigma_X)
                if len(P.X) > 0:
                    return eu.create('prob', [P.Y, sigmaXExp])
                # P(y)
                else:
                    return eu.create('prob', [P.Y])

        # P(y | z, w; sigma_X, sigma_Z')
        elif rule == 2:
            ZW = su.union(P.Z, P.W, 'name')
            sigmaZprimeExp = self.createSigmaExpression(P.Z, True)

            if len(P.X) > 0:
                sigmaXExp = self.createSigmaExpression(P.X)
                sigmaExp = eu.create('concat', [sigmaXExp, sigmaZprimeExp])

                return eu.create('prob', [P.Y, eu.create('concat', [ZW, '; ', sigmaExp])])
            else:
                return eu.create('prob', [P.Y, eu.create('concat', [ZW, '; ', sigmaZprimeExp])])                

        # P(y | w; sigma_X, sigma_Z')
        elif rule == 3:
            sigmaZprimeExp = self.createSigmaExpression(P.Z, True)

            if len(P.X) > 0:
                sigmaXExp = self.createSigmaExpression(P.X)
                sigmaExp = eu.create('concat', [sigmaXExp, sigmaZprimeExp])

                if len(P.W) > 0:
                    return eu.create('prob', [P.Y, eu.create('concat', [P.W, '; ', sigmaExp])])
                else:
                    return eu.create('prob', [P.Y, sigmaExp])

            else:
                if len(P.W) > 0:
                    return eu.create('prob', [P.Y, eu.create('concat', [P.W, '; ', sigmaZprimeExp])])
                else:
                    return eu.create('prob', [P.Y, sigmaZprimeExp])
                
    
    # SigmaCalculusRuleQuery
    # Expression
    def writeIndependenceExpression(self, query, graph = None, metadata = {}):
        rule = query.rule
        P = query.P

        # (Y \indep T | W) in G_sigma_X
        if rule == 1:
            sigmaXExp = self.createSigmaExpression(P.X)

            GsigmaXExp = None

            if len(P.X) > 0:
                GsigmaXExp = eu.create('concat', ['G_{', sigmaXExp, '}'])
            else:
                GsigmaXExp = eu.create('concat', ['G'])

            return eu.create('indep', [P.Y, P.Z, P.W, GsigmaXExp])

        # (Y \indep Z | W) in	G_sigma_X sigma_Z  \underline(Z)
        #                     & G_sigma_X sigma_Z' \underline(Z)
        elif rule == 2:
            sigmaXExp = self.createSigmaExpression(P.X)
            sigmaZExp = self.createSigmaExpression(P.Z)
            sigmaZprimeExp = eu.create('concat', [sigmaZExp, '^{\'}'])

            GsigmaXZExp = None
            GsigmaXZprimeExp = None

            if len(P.X) > 0:
                GsigmaXZExp = eu.create('concat', ['G_{', sigmaXExp, sigmaZExp, '\\underline{', P.Z, '}}'])
                GsigmaXZprimeExp = eu.create('concat', ['G_{', sigmaXExp, sigmaZprimeExp, '\\underline{', P.Z, '}}'])
            else:
                GsigmaXZExp = eu.create('concat', ['G_{', sigmaZExp, '\\underline{', P.Z, '}}'])
                GsigmaXZprimeExp = eu.create('concat', ['G_{', sigmaZprimeExp, '\\underline{', P.Z, '}}'])

            leftExp = eu.create('indep', [P.Y, P.Z, P.W, GsigmaXZExp])
            rightExp = eu.create('indep', [P.Y, P.Z, P.W, GsigmaXZprimeExp])

            return eu.create('list', [leftExp, rightExp])

        # (Y \indep Z | W) in G_sigma_X sigma_Z  \overline(Z(W))
        #                   & G_sigma_X sigma_Z' \overline(Z(W))
        elif rule == 3:
            if len(P.W) > 0:
                sigmaX = metadata['sigmaX'] if metadata and 'sigmaX' in metadata else []
                Tx = self.getTransformNodes(1, sigmaX, graph)
                GsigmaX = gu.transform(graph, Tx.over, Tx.under, Tx.overExcept, Tx.underExcept)
                AnW = gu.ancestors(P.W, GsigmaX)
                ZW = su.difference(P.Z, AnW, 'name')

                ZWExp = eu.create('concat', [ZW])
            else:
                ZWExp = eu.create('concat', [P.Z])

            sigmaXExp = self.createSigmaExpression(P.X)
            sigmaZExp = self.createSigmaExpression(P.Z)
            sigmaZprimeExp = eu.create('concat', [sigmaZExp, '^{\'}'])

            GsigmaXZExp = None
            GsigmaXZprimeExp = None

            if len(P.X) > 0:
                GsigmaXZExp = eu.create('concat', ['G_{', sigmaXExp, sigmaZExp, '\\overline{', ZWExp, '}}'])
                GsigmaXZprimeExp = eu.create('concat', ['G_{', sigmaXExp, sigmaZprimeExp, '\\overline{', ZWExp, '}}'])
            else:
                GsigmaXZExp = eu.create('concat', ['G_{', sigmaZExp, '\\overline{', ZWExp, '}}'])
                GsigmaXZprimeExp = eu.create('concat', ['G_{', sigmaZprimeExp, '\\overline{', ZWExp, '}}'])

            leftExp = eu.create('indep', [P.Y, P.Z, P.W, GsigmaXZExp])
            rightExp = eu.create('indep', [P.Y, P.Z, P.W, GsigmaXZprimeExp])

            return eu.create('list', [leftExp, rightExp])


    #  * Rule 1: G_sigma_X
    #  * Rule 2: 1) G_sigma_X sigma_Z \underline(Z), 2) G_sigma_X sigma_Z' \underline(Z)
    #  * Rule 3: 1) G_sigma_X sigma_Z \overline(Z(W)), 2) G_sigma_X sigma_Z' \overline(Z(W))
    # number, Intervention[], Graph, any
    # TransformNodes
    def getTransformNodes(self, rule, intvs, graph, metadata = None):
        result = self.interventionsToTransformNodes(intvs)

        # intvs = sigma_X
        if rule == 1:
            result.over = su.unique(result.over)
            result.overExcept = su.unique(result.overExcept)

            # all sigma nodes are exceptions
            sigmaNodes = list(filter(lambda n: n['type_'] == interventionNodeType.id_, graph.nodes))

            result.overExcept = su.union(result.overExcept, sigmaNodes, 'name')

            return result

        # intvs = sigma_X & sigma_Z or sigma_X & sigma_Zprime
        # add \underline(Z)
        elif rule == 2:
            Z = metadata['P'].Z if metadata and 'P' in metadata else []

            result.under = su.unique(result.under + Z)
            result.over = su.unique(result.over)
            result.overExcept = su.unique(result.overExcept)

            # all sigma nodes are exceptions
            sigmaNodes = list(filter(lambda n: n['type_'] == interventionNodeType.id_, graph.nodes))

            result.overExcept = su.union(result.overExcept, sigmaNodes, 'name')

            return result

        # intvs = sigma_X & sigma_Z or sigma_X & sigma_Zprime
        # add \overline(Z(W))
        elif rule == 3:
            Z = metadata['P'].Z if metadata and 'P' in metadata else []
            W = metadata['P'].W if metadata and 'P' in metadata else []
            sigmaX = metadata['sigmaX'] if metadata and 'sigmaX' in metadata else []

            Tx = self.getTransformNodes(1, sigmaX, graph)
            GsigmaX = gu.transform(graph, Tx.over, Tx.under, Tx.overExcept, Tx.underExcept)
            AnW = gu.ancestors(W, GsigmaX)
            ZW = su.difference(Z, AnW, 'name')

            result.over = su.unique(result.over + ZW)
            result.overExcept = su.unique(result.overExcept)

            # all sigma nodes are exceptions
            sigmaNodes = list(filter(lambda n: n['type_'] == interventionNodeType.id_, graph.nodes))

            result.overExcept = su.union(result.overExcept, sigmaNodes, 'name')

            return result


    # Intervention[]
    # TransformNodes
    def interventionsToTransformNodes(self, intvs):
        tx = TransformNodes()

        for intv in intvs:
            if intv.type_ == InterventionType.idle:
                continue

            # \bar_X except sigma
            elif intv.type_ == InterventionType.atomic:
                tx.over.append(intv.target)

                if intv.node is not None:
                    tx.overExcept.append(intv.node)

            # \bar_X except sigma, parents
            elif intv.type_ == InterventionType.conditional or intv.type_ == InterventionType.stochastic:
                tx.over.append(intv.target)
                tx.overExcept = tx.overExcept + intv.inputParents

                if intv.node is not None:
                    tx.overExcept.append(intv.node)

        return tx


    # Node[], bool
    # Expression
    def createSigmaExpression(self, nodes, apostrophe = False):
        if not nodes:
            return None

        parts = []

        for node in nodes:
            part = eu.create('coef', ['sigma', node])

            if apostrophe:
                part = eu.create('concat', [part, '^{\'}'])

            parts.append(part)

        return eu.create('concat', parts)


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