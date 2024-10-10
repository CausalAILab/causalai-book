from src.graph.classes.graph_defs import latentNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation
from src.inference.adjustment.generalized_adjustment import GeneralizedAdjustment, GeneralizedAdjustmentName
from src.inference.classes.trace import Trace
from src.inference.classes.failure import Failure

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.compute.compute_utils import ComputeUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.transportability_utils import TransportabilityUtils


alg_name = 'Generalized Adjustment'
ga_base = 0
ga_rule2 = 2
ga_rule3 = 3
ga_sum_over = 4
ga_recover = 5


class GeneralizedAdjustmentEngine(BaseEngine):

    #     private P: Expression;
    #     private externalData: Node[];
    #     private latentNodes: Node[];
    #     private latentNodeNames: string[];
    #     private populations: Population[];
    #     private experimentSpecs: ExperimentSpecs;

    def __init__(self):
        super().__init__()

        self.P = None
        self.externalData = None
        self.latentNodes = []
        self.latentNodeNames = []
        self.populations = []
        self.experimentSpecs = dict()

    # CausalQuery, Graph, EngineConfiguration
    # boolean

    def canCompute(self, query, G, config={}):
        if not query or not G:
            return False

        if 'simplifyWhenPossible' in config and config['simplifyWhenPossible'] == False:
            return False

        # graph = pu.projectOverNonLatentNodes(G)
        graph = G

        unsupportedNodes = su.difference(
            graph.nodes, gu.filterBasicNodes(graph.nodes), 'name')

        if len(unsupportedNodes) > 0:
            if len(unsupportedNodes) == 1:
                S = cu.getSelectionBiasNode(graph)

                if S is None:
                    return False

                if S is not None and not cu.inSBContext(graph):
                    return False

                return True
            else:
                return False

        return False

    # returns Expression | Failure<Any>

    def compute(self, query, G, config=None):
        self.populations = config['populations'] if config is not None and 'populations' in config else [
            targetPopulation]
        self.experimentSpecs = config['experimentSpecs'] if config is not None and 'experimentSpecs' in config else {
        }
        self.externalData = config['externalData'] if config is not None and 'externalData' in config else [
        ]

        self.clearTrace()

        if config is not None and 'simplifyWhenPossible' in config and config['simplifyWhenPossible'] == False:
            return None

        # implement projectOverNonLatentNodes
        # graph = pu.projectOverNonLatentNodes(G)
        graph = G
        self.currentQuery = query
        self.latentNodes = list(
            filter(lambda n: n['type_'] == latentNodeType.id_, graph.nodes))
        self.latentNodeNames = list(map(lambda n: n['name'], self.latentNodes))

        [y, z, x] = self.normalizeQuery(query, graph)

        conditional = z is not None and not su.isEmpty(z)

        if conditional:
            return self.createFailureMessage()

        V = gu.filterBasicNodes(graph.nodes)
        V = sorted(V, key=lambda n: n['name'])
        S = cu.getSelectionBiasNode(graph)

        self.P = eu.create(
            'prob', [gu.nodesToVariables(V), [eu.create('=', [S, '1'])]])

        adjustment = GeneralizedAdjustment.findAdjustment(
            graph, x, y, self.externalData, self.P)

        if adjustment is None:
            return self.createFailureMessage()

        Z = adjustment['covariates']
        ZT = adjustment['external']
        ZS = su.difference(Z, ZT, 'name')

        xVars = gu.nodesToVariables(x)
        yVars = gu.nodesToVariables(y)
        zVars = gu.nodesToVariables(Z)
        ztVars = gu.nodesToVariables(ZT)
        zsVars = gu.nodesToVariables(ZS)

        isZEmpty = su.isEmpty(Z)
        isZTEmpty = su.isEmpty(ZT)
        isZSEmpty = su.isEmpty(ZS)

        # sum_zt P_x(y|zt) P_x(zt)
        step1SumOverZTExp = eu.create('sum', [ZT, None, eu.create('product', [
            eu.create('prob', [yVars, ztVars, xVars]),
            eu.create('prob', [ztVars, None, xVars])
        ])])

        # sum_zt P_x(y|zt) P(zt)
        step2Rule3Exp = eu.create('sum', [ZT, None, eu.create('product', [
            eu.create('prob', [yVars, ztVars, xVars]),
            eu.create('prob', [ztVars])
        ])])

        # sum_zt P_x(y|zt,S=1) P(zt)
        # P_x(y|S=1)
        SExp = eu.create('=', [S, '1'])
        yGivenZTSDoXExp = eu.create('prob', [yVars, SExp, xVars]) if isZTEmpty else eu.create(
            'prob', [yVars, eu.create('list', [ztVars, SExp]), xVars])
        ztExp = None if isZTEmpty else eu.create('prob', [ztVars])
        step3RecoverExp = eu.create('sum', [ZT, None, eu.create('product', [
            yGivenZTSDoXExp,
            ztExp
        ])])

        # sum_z P_x(y|z,S=1) P_x(zs|zt,S=1) P(zt)
        # sum_z P_x(y|z,S=1) P_x(zs|S=1)
        # P_x(y|S=1)
        yGivenZSDoXExp = eu.create('prob', [yVars, SExp, xVars]) if isZEmpty else eu.create(
            'prob', [yVars, eu.create('list', [zVars, SExp]), xVars])
        zsGivenZTSDoXExp = None

        if not isZSEmpty:
            zsGivenZTSDoXExp = eu.create('prob', [zsVars, SExp, xVars]) if isZTEmpty else eu.create(
                'prob', [zsVars, eu.create('list', [ztVars, SExp]), xVars])

        step4SumOverExp = eu.create('sum', [Z, None, eu.create('product', [
            yGivenZSDoXExp,
            zsGivenZTSDoXExp,
            ztExp
        ])])

        # sum_z P(y|x,z,S=1) P(zs|zt,S=1) P(zt)
        # sum_z P(y|x,z,S=1) P(zs|S=1)
        # P_x(y|S=1)
        zsGivenZTSExp = None

        if not isZSEmpty:
            zsGivenZTSExp = eu.create('prob', [zsVars, SExp]) if isZTEmpty else eu.create(
                'prob', [zsVars, eu.create('list', [ztVars, SExp])])

        step5Rule3Exp = eu.create('sum', [Z, None, eu.create('product', [
            yGivenZSDoXExp,
            zsGivenZTSExp,
            ztExp
        ])])

        step6Rule2Exp = adjustment['expression']

        resultExp = adjustment['expression']
        simplifyExpression = None

        if isZEmpty:
            simplifyExpression = eu.create('text', [
                                           'Obtained by ' + adjustment['name'] + ' with an adjustment pair $(\\emptyset, \\emptyset)$'])
        elif isZTEmpty:
            simplifyExpression = eu.create('text', [
                                           'Obtained by ' + adjustment['name'] + ' with an adjustment pair $(\\lbrace', Z, '\\rbrace, \\emptyset)$'])
        else:
            simplifyExpression = eu.create('text', [
                                           'Obtained by ' + adjustment['name'] + ' with an adjustment pair $(\\lbrace', Z, '\\rbrace, \\lbrace', ZT, '\\rbrace)$'])

        rootTrace = Trace()
        rootTrace.query = self.createPExpression(y, z, x, 0, None)
        rootTrace.result = resultExp
        rootTrace.algorithmInfo = {
            'algName': alg_name, 'line': ga_base, 'args': {
                'populations': ou.clone(self.populations),
                'experiments': ou.clone(self.experimentSpecs),
                'adjustment_name': adjustment['name'],
                'adjustment': {
                    'covariates': Z,
                    'external': ZT
                }
            }
        }
        rootTrace.children = []
        rootTrace.simplification = simplifyExpression

        # sumover ZT
        step1SumOverTrace = Trace()
        step1SumOverTrace.query = step1SumOverZTExp
        step1SumOverTrace.result = None
        step1SumOverTrace.algorithmInfo = {
            'algName': alg_name, 'line': ga_sum_over, 'args': {
                'S': ZT
            }
        }
        step1SumOverTrace.children = []

        # rule 3   ZT indep X in G_bar_X
        step2Rule3Trace = Trace()
        step2Rule3Trace.query = step2Rule3Exp
        step2Rule3Trace.result = None
        step2Rule3Trace.algorithmInfo = {
            'algName': alg_name, 'line': ga_rule3, 'args': {
                'indeps': [
                    eu.create('indep', [ZT, x, None, eu.create(
                        'concat', ['G_{\\overline{', x, '}}'])])
                ]
            }
        }
        step2Rule3Trace.subgraph = {'V': su.union(gu.nodeToList(
            graph.nodes), self.latentNodeNames), 'over': gu.nodeToList(x)}
        step2Rule3Trace.children = []

        # recover  Y indep S | ZT in G^pbd(X,Y)
        step3RecoverTrace = Trace()
        step3RecoverTrace.query = step3RecoverExp
        step3RecoverTrace.result = None
        step3RecoverTrace.algorithmInfo = {
            'algName': alg_name, 'line': ga_recover, 'args': {
                'indeps': [
                    eu.create('indep', [y, S, ZT, eu.create(
                        'concat', ['G_{\\underline{', x, '}}'])])
                ]
            }
        }
        step3RecoverTrace.subgraph = {'V': su.union(gu.nodeToList(
            graph.nodes), self.latentNodeNames), 'under': gu.nodeToList(x)}
        step3RecoverTrace.children = []

        # sumover ZS
        step4SumOverTrace = Trace()
        step4SumOverTrace.query = step4SumOverExp
        step4SumOverTrace.result = None
        step4SumOverTrace.algorithmInfo = {
            'algName': alg_name, 'line': ga_sum_over, 'args': {
                'S': ZS
            }
        }
        step4SumOverTrace.children = []

        # rule 3   ZS indep X given ZT,S in G_bar_X
        step5Rule3Trace = Trace()
        step5Rule3Trace.query = step5Rule3Exp
        step5Rule3Trace.result = None
        step5Rule3Trace.algorithmInfo = {
            'algName': alg_name, 'line': ga_rule3, 'args': {
                'indeps': [
                    eu.create('indep', [ZS, x, su.union(ZT, [S], 'name'), eu.create(
                        'concat', ['G_{\\overline{', x, '}}'])])
                ]
            }
        }
        step5Rule3Trace.subgraph = {'V': su.union(gu.nodeToList(
            graph.nodes), self.latentNodeNames), 'over': gu.nodeToList(x)}
        step5Rule3Trace.children = []

        # rule 2   X indep Y | Z,S in G_X_bar
        step6Rule2Trace = Trace()
        step6Rule2Trace.query = step6Rule2Trace
        step6Rule2Trace.result = None
        step6Rule2Trace.algorithmInfo = {
            'algName': alg_name, 'line': ga_rule2, 'args': {
                'indeps': [
                    eu.create('indep', [x, y, su.union(Z, [S], 'name'), eu.create(
                        'concat', ['G_{\\underline{', x, '}}'])])
                ]
            }
        }
        step6Rule2Trace.subgraph = {'V': su.union(gu.nodeToList(
            graph.nodes), self.latentNodeNames), 'under': gu.nodeToList(x)}
        step6Rule2Trace.children = []

        # sumover ZT
        # rule 3   ZT indep X in G_bar_X
        # recover  Y indep S | ZT in G^pbd(X,Y)
        # sumover ZS
        # rule 3   ZS indep X given ZT,S in G_bar_X
        # rule 2   X indep Y | Z,S in G_X_bar

#         // sum_zt P_x(y|zt) P_x(zt)
#         // sum_zt P_x(y|zt) P(zt)
#         // sum_zt P_x(y|zt,S=1) P(zt)
#         // sum_z P_x(y|z,S=1) P_x(zs|zt,S=1) P(zt)
#         // sum_z P_x(y|z,S=1) P(zs|zt,S=1) P(zt)
#         // sum_z P(y|x,z,S=1) P(zs|zt,S=1) P(zt)

#         // organize trace hierarchy
#         // if Z empty, step 3,6
#         // else
#         //  if ZT empty, step 3,4,5,6
#         //  if ZS empty, step 1,2,3,6
#         //  else regular steps

        if isZEmpty:
            rootTrace.children = [step3RecoverTrace]
            step3RecoverTrace.children = [step6Rule2Trace]
        else:
            if isZTEmpty:
                rootTrace.children = [step3RecoverTrace]
                step3RecoverTrace.children = [step4SumOverTrace]
                step4SumOverTrace.children = [step5Rule3Trace]
                step5Rule3Trace.children = [step6Rule2Trace]
            elif isZSEmpty:
                rootTrace.children = [step1SumOverTrace]
                step1SumOverTrace.children = [step2Rule3Trace]
                step2Rule3Trace.children = [step3RecoverTrace]
                step3RecoverTrace.children = [step6Rule2Trace]
            else:
                rootTrace.children = [step1SumOverTrace]
                step1SumOverTrace.children = [step2Rule3Trace]
                step2Rule3Trace.children = [step3RecoverTrace]
                step3RecoverTrace.children = [step4SumOverTrace]
                step4SumOverTrace.children = [step5Rule3Trace]
                step5Rule3Trace.children = [step6Rule2Trace]

        self.pushTrace(rootTrace)
        self.numberTrace(rootTrace)

        return resultExp

    # Dict[str, AlgorithmTracer]

    def getAlgorithmTracers(self):
        return {
            # 'Generalized Adjustment': GeneralizedAdjustmentAlgorithmTracer()
            'Generalized Adjustment': None
        }

    def createPExpression(self, scope, conditional=None, intervention=None, domain=0, experiments=None):
        return self.setScripts(eu.create('prob', [scope, su.difference(conditional, experiments, 'name'), intervention]), experiments)

    def setScripts(self, P, experiments):
        return TransportabilityUtils.setScripts(P, experiments, None)

    def createFailureMessage(self):
        failureExp = eu.create('concat', [
            eu.create('text', ['The recoverability of ']),
            eu.create('prob', [self.currentQuery.y,
                      self.currentQuery.z, self.currentQuery.x]),
            eu.create('text', [' cannot be determined.'])
        ])

        return Failure(failureExp, None)
