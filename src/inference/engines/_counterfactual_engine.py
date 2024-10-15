import functools

from src.graph.classes.graph_defs import latentNodeType
from src.graph_analysis.sigma_calculus.sigma_calculus_utils import SigmaCalculusUtils
from src.inference.classes.causal_query import CausalQuery
from src.inference.engines.base_engine import BaseEngine
from src.inference.engines.sigma_calculus_engine import SigmaCalculusEngine
from src.intervention.classes.intervention import Intervention
from src.intervention.classes.intervention_type import InterventionType
from src.intervention.classes.intervention import interventionNodeType
from src.transportability.classes.transportability import targetPopulation
from src.inference.classes.failure import Failure
from src.inference.utils.graph_utils import sortByName

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.inference.utils.counterfactual_utils import CounterfactualUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.transportability_utils import TransportabilityUtils
from src.inference.utils.confounding_analysis import ConfoundingAnalysis


alg_name = 'cf-id'


class CounterfactualEngine(BaseEngine):

    # private populations: Population[];
    # private experiments: Node[][][];
    # private originalGraph: Graph;
    # private P: Expression;
    # private latentNodes: Node[];
    # private latentNodeNames: string[];

    def __init__(self):
        super().__init__()

        self.P = None
        self.V = []
        self.latentNodes = []
        self.latentNodeNames = []
        self.originalGraph = None
        self.selectionDiagram = None
        self.populations = []
        # self.experiments = None
        self.mapFactorValues = []
        self.sumOver = []
        self.config = None

    # CausalQuery, Graph, EngineConfiguration
    # boolean

    def canCompute(self, query, G, config=None):
        if not query or not G:
            return False

        if not su.isEmpty(query.z):
            return False

        unsupportedNodes = su.difference(
            G.nodes, gu.filterBasicNodes(G.nodes, False), 'name')

        if len(unsupportedNodes) > 0:
            return False

        return True

    # Expression | Failure<Any>

    def compute(self, query, G, config=None):
        self.populations = config['populations'] if config is not None and 'populations' in config else [
            targetPopulation]
        # for ctf-ID
        self.experiments = config['experiments'] if config is not None and 'experiments' in config else [
        ]
        self.experimentSpecs = config['experimentSpecs'] if config is not None and 'experimentSpecs' in config else {
        }
        # for ctf-TR
        # self.interventions = config['interventions'] if config is not None and 'interventions' in config else [
        # ]
        # self.interventionSpecs = config['interventionSpecs'] if config is not None and 'interventionSpecs' in config else {
        # }
        self.config = config
        self.mapFactorValues = []
        self.sumOver = []

        self.clearTrace()

        graph = ProjectionUtils.projectOverNonLatentNodes(G)

        self.selectionDiagram = graph
        self.originalGraph = graph = self.simplifyGraph(graph)
        self.latentNodes = list(
            filter(lambda n: n['type_'] == latentNodeType.id_, graph.nodes))
        self.latentNodeNames = list(map(lambda n: n['name'], self.latentNodes))

        self.currentQuery = ou.clone(query)

        self.V = sorted(graph.nodes, key=sortByName)
        # for ctf-TR - write all available distributions
        # self.P = self.setScripts(
        #     eu.create('prob', [gu.nodesToVariables(self.V)]), 0, None)

        try:
            self.popTrace()
            result = self.identifyCond(query.y, query.x, self.P, graph)
            result = pu.simplify(result)
            result = self.assignValues(result)

            if config is not None and 'renameReinstantiatedVariables' in config and config['renameReinstantiatedVariables'] == True:
                self.distinguishVariables(result, self.replaceVariables)

            return result
        except Exception as error:
            if self.getTrace() is not None:
                self.getTrace().result = error

            return error

    # Counterfactual[], Counterfactual[], Expression, Graph
    # Expression
    def identifyCond(self, Ystar, Xstar, P, G):
        if Xstar is None or su.isEmpty(Xstar):
            return self.identify(Ystar, P, G)

        Ystar, summed = cu.unnest(Ystar)
        self.sumOver.extend(summed)
        Xstar, summed = cu.unnest(Xstar)
        self.sumOver.extend(summed)

        VY = cu.V(Ystar)
        VX = cu.V(Xstar)
        XYstar = su.union(Ystar, Xstar)

        A = cu.getAncestralComponents(XYstar, Xstar, G)

        D = []
        # print('ancestral components')
        # for Ai in A:
        #     cu.print(Ai)
        for Ai in A:
            if len(su.intersection(VY, cu.V(Ai), 'name')) > 0:
                D.extend(cu.factorize(Ai, G))

        # some of the interventions added due to ctf-factorization may not have proper values assigned
        # try to find those values from given counterfactuals Ystar and Xstar
        for Dx in D:
            for intv in Dx.interventions:
                if intv.value is None:
                    matching = list(filter(lambda Yx: su.equals(
                        [Yx.variable], [intv.variable], 'name'), XYstar))

                    if len(matching) == 0:
                        continue

                    intv.value = matching[0].value
        # print('D')
        # for Di in D:
        #     cu.print(Di)
        Q = self.identify(D, P, G)

        VD = cu.V(D)

        num = pu.sumOver(Q, su.difference(
            VD, su.union(VY, VX, 'name'), 'name'))
        den = pu.sumOver(ou.clone(Q), su.difference(VD, VX, 'name'))

        return eu.create('frac', [num, den])

    # Counterfactual[], Expression, Graph
    # Expression

    def identify(self, Ystar, P, G):
        V = gu.topoSort(G, True)
        V = gu.filterBasicNodes(V)
        self.V = V

        Ystar, summed = cu.unnest(Ystar)
        # print('after unnest')
        # cu.print(Ystar)
        Ystar = cu.simplify(Ystar, G)

        if Ystar == 0:
            return eu.create('text', ['0'])

        # print('after simplify')
        # cu.print(Ystar)
        Wstar = cu.An(Ystar, G)
        # print('Wstar')
        # cu.print(Wstar)
        Wstar = cu.factorize(Wstar, G)
        # print('factorize')
        # cu.print(Wstar)

        VW = cu.V(Wstar)
        G_W = gu.subgraph(G, VW)
        C = cu.cComponents(Wstar, G_W)
        # print('c-comp')
        # for Ci in C:
        #     cu.print(Ci)
        for Ci in C:
            if not cu.isConsistent(Ci):
                raise self.createFailureMessage(G)

        WmY = su.difference(VW, cu.V(Ystar), 'name')
        sumOver = su.union(summed, WmY, 'name')
        self.sumOver.extend(sumOver)
        # print('summed')
        # print(summed)
        # print(sumOver)

        factors = []
        domains = self.populations
        # ctf-ID
        Zcollection = self.experiments

        # ctf-TR
        # Zcollection = self.interventions

        # sigmaCalcEngine = SigmaCalculusEngine()

        for Ci in C:
            VCi = cu.V(Ci)

            # # ctf-TR
            # # treatment = atomic interventions on V \ Ci
            # PaCi = gu.parents(VCi, G)
            # PaCi = su.difference(PaCi, VCi, 'name')
            # VmCi = PaCi
            # # VmCi = su.difference(V, VCi, 'name')

            # intvsTreatment = []

            # for n in VmCi:
            #     intv = Intervention(None, n, InterventionType.atomic)
            #     intvsTreatment.append(intv)

            # Gsigma = SigmaCalculusUtils.createGraphSigma(G, intvsTreatment)

            # for intv in intvsTreatment:
            #     nodeName = intv.target['name']
            #     sigmaNodeName = '\\sigma_' + \
            #         nodeName if len(
            #             nodeName) == 1 else '\\sigma_{' + nodeName + '}'
            #     intv.node = gu.getNodeByName(sigmaNodeName, Gsigma)
            #     intv.target = gu.getNodeByName(nodeName, Gsigma)

            #     if 'metadata' not in intv.node:
            #         intv.node['metadata'] = {}

            #     # match sigma nodes and the domain it belongs
            #     popLabels = []

            #     for pop in self.populations:
            #         found = False

            #         Zcollection = self.interventionSpecs[pop.label]
            #         # assuming 1 collection of intervention per population
            #         intvDistribution = Zcollection[0]

            #         for itv in intvDistribution:
            #             if su.equals([intv.target], [itv.target], 'name') and intv.type_ == itv.type_:
            #                 if intv.type_ == InterventionType.conditional or intv.type_ == InterventionType.stochastic:
            #                     if su.equals(intv.inputParents, itv.inputParents, 'name'):
            #                         found = True
            #                         break
            #                 else:
            #                     found = True
            #                     break

            #         if found:
            #             popLabels.append(pop.label)

            #     intv.node['metadata']['populations'] = popLabels

            # query = CausalQuery(VmCi, VCi, [], intvsTreatment)
            # print('query')
            # print(VCi)

            # # explicitly call sigmaTR
            # try:
            #     QCi = sigmaCalcEngine.compute(query, G, self.config)
            # except:
            #     raise self.createFailureMessage(G)

            # # alternative: can we call Identify instead?

            # if QCi is not None:
            #     if isinstance(QCi, Failure):
            #         raise self.createFailureMessage(G)

            #     print('sigmaTR result')
            #     print(eu.write(pu.simplify(QCi)))

            #     factors.append(QCi)
            #     self.mapFactorValues.append(
            #         {'factor': QCi, 'ctf': Ci, 'variables': VCi})
            #     continue

            # raise self.createFailureMessage(G)

            # ctf-ID
            solved = False

            for i in range(len(domains)):
                if solved:
                    break

                Zi = Zcollection[i]

                # for Zintvs in Zi:
                for Z in Zi:

                    # Z = []

                    # for intv in Zintvs:
                        # Z = su.union(Z, intv.target, 'name')

                    if len(su.intersection(VCi, Z, 'name')) > 0:
                        continue

                    GZbar = gu.transform(G, Z, None)
                    CB = gu.cCompDecomposition(GZbar)

                    Bi = None

                    for Bk in CB:
                        if su.isSubset(VCi, Bk, 'name'):
                            Bi = Bk
                            break

                    if Bi is None:
                        continue

                    PzV = self.createPExpression(V, [], Z, i, [])
                    QBi = ConfoundingAnalysis.qComputeCComp(Bi, V, PzV)
                    GBi = gu.subgraph(G, Bi)
                    QCi = self.qIdentify(VCi, Bi, QBi, GBi)
                    # print('query')
                    # print(VCi)
                    # print(Z)
                    # print(eu.write(QCi))
                    if QCi is not None:
                        solved = True
                        factors.append(QCi)
                        self.mapFactorValues.append(
                            {'factor': QCi, 'ctf': Ci, 'variables': VCi})
                        break

            if not solved:
                raise self.createFailureMessage(G)

        factors.reverse()

        # sort c-factors with summations at the end
        def sortBySummation(f1, f2):
            if f1.type_ == 'sum' and f2.type_ != 'sum':
                return 1
            elif f1.type_ != 'sum' and f2.type_ == 'sum':
                return -1
            else:
                return 0

        factors = sorted(factors, key=functools.cmp_to_key(sortBySummation))

        return pu.sumOver(eu.create('product', factors), sumOver)

    def qIdentify(self, C, T, Q, G):
        A = su.intersection(gu.ancestors(C, gu.subgraph(G, T)), T, 'name')

        if su.equals(A, C):
            return pu.sumOver(Q, su.difference(T, C, 'name'))
        elif su.equals(A, T):
            return None
        else:
            QA = pu.sumOver(Q, su.difference(T, A, 'name'))
            G_A = gu.subgraph(G, A)
            CG_A = gu.cCompDecomposition(G_A)

            for Tip in CG_A:
                if su.isSubset(C, Tip, 'name'):
                    Ti = su.intersection(Tip, A, 'name')
                    QTi = ConfoundingAnalysis.qComputeCComp(
                        Ti, su.intersection(self.V, A, 'name'), QA)
                    G_Ti = gu.subgraph(G, Ti)

                    return self.qIdentify(C, Ti, QTi, G_Ti)

    def getVariablesInFactor(self, exp):
        if exp is None:
            return []

        if exp.type_ == 'prob':
            return exp.parts[0]
        elif exp.type_ == 'sum':
            sumOver = exp.parts[0]
            variables = self.getVariablesInFactor(exp.parts[2])
            variables = su.difference(variables, sumOver, 'name')

            return variables
        elif exp.type_ == 'product':
            variables = []

            for part in exp.parts:
                variables.extend(self.getVariablesInFactor(part))

            return variables
        elif exp.type_ == 'frac':
            num = self.getVariablesInFactor(exp.parts[0])
            den = self.getVariablesInFactor(exp.parts[1])

            return su.union(num, den, 'name')

    # # for ctf-tr
    # def assignValues(self, P):
    #     if P is None:
    #         return None

    #     # non-cond
    #     if P.type_ == 'sum':
    #         exp = P.parts[2]

    #         if exp.type_ == 'product':
    #             parts = []

    #             for factor in exp.parts:
    #                 print('factor')
    #                 print(factor.type_)
    #                 print(eu.write(factor))
    #                 found = False
    #                 factorWithValuesReplaced = None

    #                 variables = self.getVariablesInFactor(factor)
    #                 print('variable after')
    #                 print(variables)

    #                 for factorMap in self.mapFactorValues:
    #                     if su.equals(variables, factorMap['variables'], 'name'):
    #                         found = True
    #                         factorWithValuesReplaced = cu.assignValues(
    #                             factor, factorMap['ctf'], self.sumOver)
    #                         break

    #                 if found:
    #                     parts.append(factorWithValuesReplaced)
    #                 else:
    #                     parts.append(factor)

    #             exp.parts = parts
    #     # cond
    #     elif P.type_ == 'frac':
    #         P.parts[0] = self.assignValues(P.parts[0])
    #         P.parts[1] = self.assignValues(P.parts[1])
    #     elif P.type_ == 'prob':
    #         variables = P.parts[0]

    #         for factorMap in self.mapFactorValues:
    #             if su.equals(variables, factorMap['variables'], 'name'):
    #                 P = cu.assignValues(
    #                     P, factorMap['ctf'], self.sumOver)
    #                 break

    #     return P

    # for ctf-id
    def assignValues(self, P):
        if P is None:
            return None

        # non-cond
        if P.type_ == 'sum':
            exp = P.parts[2]

            if exp.type_ == 'product':
                parts = []

                for factor in exp.parts:
                    found = False
                    newFactor = None

                    # find which variables are involved in the factor
                    variables = []

                    if factor.type_ == 'prob':
                        variables.extend(factor.parts[0])
                    elif factor.type_ == 'product':
                        for part in factor.parts:
                            variables.extend(part.parts[0])

                    for factorMap in self.mapFactorValues:
                        if su.equals(variables, factorMap['variables'], 'name'):
                            found = True
                            newFactor = cu.assignValues(
                                factor, factorMap['ctf'], self.sumOver)
                            break

                    if found:
                        parts.append(newFactor)
                    else:
                        parts.append(factor)

                exp.parts = parts
        # cond
        elif P.type_ == 'frac':
            P.parts[0] = self.assignValues(P.parts[0])
            P.parts[1] = self.assignValues(P.parts[1])
        elif P.type_ == 'prob':
            variables = P.parts[0]
            newFactor = None

            for factorMap in self.mapFactorValues:
                if su.equals(variables, factorMap['variables'], 'name'):
                    newFactor = cu.assignValues(
                        P, factorMap['ctf'], self.sumOver)
                    break

        return P

    def createPExpression(self, scope, conditional=[], intervention=[], domain=0, experiments=[]):
        return self.setScripts(eu.create('prob', [
            scope,
            su.difference(conditional, experiments, 'name'),
            intervention
        ]), domain, experiments)

    def setScripts(self, P, domain, experiments):
        return TransportabilityUtils.setScripts(P, experiments, self.populations[domain] if self.populations is not None and len(self.populations) > 1 else None)

    def createFailureMessage(self, witness):
        failureExp = [
            eu.create('prob', [self.currentQuery.y, self.currentQuery.z, self.currentQuery.x]),
            eu.create('text', [' is not identifiable from ']),
            self.P,
            eu.create('text', ['.'])
        ]

        return Failure(eu.create('concat', failureExp), witness)

    def getAlgorithmTracers(self):
        return {
            # 'cf-id': CounterfactualAlgorithmTracer()
            'cf-id': None
        }
