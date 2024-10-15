from src.graph.classes.graph_defs import latentNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation
from src.inference.adjustment.backdoor_adjustment import BackdoorAdjustment, BackdoorAdjustmentName
from src.inference.classes.trace import Trace
from src.inference.classes.failure import Failure

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.compute.compute_utils import ComputeUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.transportability_utils import TransportabilityUtils


alg_name = 'backdoor'

docalc_base = 0
# 2
docalc_sum_over = 1
# 4
docalc_rule2 = 2
# 1
docalc_rule3 = 3


class BackdoorEngine(BaseEngine):

    # P: Expression
    # latentNodes: Node[]
    # latentNodeNames: str[]
    # populations: Population[]
    # experimentSpecs: ExperimentSpecs
    # libEntries: LibraryEntry[]

    def __init__(self, libEntries=[]):
        super().__init__()

        self.P = None
        self.latentNodes = []
        self.latentNodeNames = []
        self.populations = []
        self.experimentSpecs = dict()
        self.libEntries = libEntries

#     constructor(
#         private libraryService: LibraryService
#     ) {
#         super();

#         self.libraryService.getLibraryEntries().subscribe(libs => self.libEntries = libs);
#     }

    # CausalQuery, Graph, EngineConfiguration
    # boolean
    def canCompute(self, query, G, config=None):
        if not query or not G:
            return False

        # if not self.libEntries or len(libEntries) == 0:
        #     return False

        if config is not None and 'simplifyWhenPossible' in config and config['simplifyWhenPossible'] == False:
            return False

        # graph = pu.projectOverNonLatentNodes(G)
        graph = G

        unsupportedNodes = su.difference(
            graph.nodes, gu.filterBasicNodes(graph.nodes, False), 'name')

        if len(unsupportedNodes) > 0:
            if len(unsupportedNodes) == 1:
                S = cu.getSelectionBiasNode(graph)

                if S is None:
                    return False

                if S is not None and cu.inSBContext(graph):
                    return False
            else:
                return False

        populations = config['populations'] if 'populations' in config else [
            targetPopulation]

        if len(populations) > 1:
            return False

        candidates = self.findCandidateLibraryEntries(graph)

        if not candidates or len(candidates) == 0:
            return False

        # for candidate in candidates:
        #     iso = gu.findIsomorphicGraphLabels(graph, candidate.graph)

        #     if iso is not None and iso.original and iso.permuted and len(iso.original) == len(iso.permuted):
        #         return True

        [y, z, x, ] = self.normalizeQuery(query, graph)

        conditional = z is not None and not su.isEmpty(z)
        P = self.setScripts(
            eu.create('prob', [gu.nodesToVariables(graph.nodes)]), None)

        adjustment = None

        if not conditional:
            adjustment = BackdoorAdjustment.findAdjustment(graph, x, y, [], P)

        return adjustment is not None

    # Expression | Failure<Any>

    def compute(self, query, G, config=None):
        self.populations = config['populations'] if config is not None and 'populations' in config else [
            targetPopulation]
        self.experimentSpecs = config['experimentSpecs'] if config is not None and 'experimentSpecs' in config else {
        }

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
        self.P = self.setScripts(
            eu.create('prob', [gu.nodesToVariables(graph.nodes)]), None)

        adjustment = None

        if not conditional:
            adjustment = BackdoorAdjustment.findAdjustment(
                graph, x, y, [], self.P)

        if adjustment is None:
            return self.createFailureMessage(None)

        Z = adjustment['covariates']
        emptySet = Z is not None and len(Z) == 0

        rootTrace = Trace()
        resultExp = adjustment['expression']

        if emptySet:
            rule2Trace = Trace()
            rule2Trace.query = resultExp
            rule2Trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_rule2, 'args': {
                    'indeps': [
                        eu.create('indep', [x, y, Z, eu.create(
                            'concat', ['G_{\\underline{', x, '}}'])])
                    ]
                }
            }
            rule2Trace.subgraph = {
                'V': su.union(gu.nodeToList(graph.nodes), self.latentNodeNames),
                'under': gu.nodeToList(x)
            }

            rootTrace.query = self.createPExpression(y, z, x, 0, None)
            rootTrace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_base, 'args': {
                    'populations': ou.clone(self.populations), 'experiments': ou.clone(self.experimentSpecs),
                    'adjustment_name': BackdoorAdjustmentName,
                    'adjustment': {
                        'set': []
                    }
                }
            }
            rootTrace.children = [rule2Trace]
            rootTrace.simplification = eu.create(
                'text', ['Obtained by an empty admissible set'])

        else:
            # sum_z p_x(y|z) p_x(z)
            sumoverExp = eu.create('sum', [Z, None, eu.create('product', [
                eu.create('prob', [gu.nodesToVariables(
                    y), gu.nodesToVariables(Z), gu.nodesToVariables(x)]),
                eu.create('prob', [gu.nodesToVariables(
                    Z), None, gu.nodesToVariables(x)])
            ])])

            # sum_z p(y|x,z) p_x(z)
            rule2Exp = eu.create('sum', [Z, None, eu.create('product', [
                eu.create('prob', [gu.nodesToVariables(y),
                          gu.nodesToVariables(su.union(x, Z))]),
                eu.create('prob', [gu.nodesToVariables(
                    Z), None, gu.nodesToVariables(x)])
            ])])

            rule3Trace = {
                'query': resultExp, 'result': None,
                'algorithmInfo': {
                    'algName': alg_name, 'line': docalc_rule3, 'args': {
                        'indeps': [
                            eu.create('indep', [x, Z, None, eu.create(
                                'concat', ['G_{\\overline{', x, '}}'])])
                        ]
                    }
                },
                'subgraph': {
                    'V': su.union(gu.nodeToList(graph.nodes), self.latentNodeNames),
                    'over': gu.nodeToList(x)
                }
            }

            rule2Trace = {
                'query': rule2Exp, 'result': None,
                'algorithmInfo': {
                    'algName': alg_name, 'line': docalc_rule2, 'args': {
                        'indeps': [
                            eu.create('indep', [x, y, Z, eu.create(
                                'concat', ['G_{\\underline{', x, '}}'])])
                        ]
                    }
                },
                'subgraph': {
                    'V': su.union(gu.nodeToList(graph.nodes), self.latentNodeNames),
                    'under': gu.nodeToList(x)
                },
                'children': [rule3Trace]
            }

            sumOverTrace = {
                'query': sumoverExp, 'result': None,
                'algorithmInfo': {
                    'algName': alg_name, 'line': docalc_sum_over, 'args': {
                        'S': adjustment['covariates']
                    }
                },
                'children': [rule2Trace]
            }

            rootTrace.query = self.createPExpression(y, z, x, 0, None)
            rootTrace.result = resultExp
            rootTrace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_base, 'args': {
                    'populations': ou.clone(self.populations),
                    'experiments': ou.clone(self.experimentSpecs),
                    'adjustment_name': BackdoorAdjustmentName,
                    'adjustment': {
                        'set': adjustment['covariates']
                    }
                }
            }
            rootTrace.children = [sumOverTrace]
            rootTrace.simplification = eu.create('text', ['Obtained by ' + adjustment['name'] + ' with an admissible set ',
                                                 '$' if emptySet else '$\\lbrace', '\\emptyset' if emptySet else adjustment['covariates'], '$' if emptySet else '\\rbrace$'])

        self.pushTrace(rootTrace)
        self.numberTrace(rootTrace)

        return resultExp

    # Dict[str, AlgorithmTracer]

    def getAlgorithmTracers(self):
        return {
            # 'backdoor': DoCalculusAlgorithmTracer()
            'backdoor': None
        }

    def findCandidateLibraryEntries(self, graph):
        if not graph or not self.libEntries or len(self.libEntries) == 0:
            return []

        found = []

        for lib in self.libEntries:
            # projected = pu.projectOverNonLatentNodes(lib.graph)
            projected = lib.graph

            if not gu.equals(graph, projected):
                continue

            found.append(lib)

        return found

    def createPExpression(self, scope, conditional=None, intervention=None, domain=0, experiments=None):
        return self.setScripts(eu.create('prob', [scope, su.difference(conditional, experiments, 'name'), intervention]), experiments)

    def setScripts(self, P, experiments):
        return TransportabilityUtils.setScripts(P, experiments, None)

    def createFailureMessage(self, witness):
        failureExp = [
            eu.create('prob', [self.currentQuery.y,
                      self.currentQuery.z, self.currentQuery.x]),
            eu.create('text', [' is not identifiable from ']),
            self.P,
            eu.create('text', ['.'])
        ]

        return Failure(eu.create('concat', failureExp), witness)
