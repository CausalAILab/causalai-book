from src.graph.classes.graph_defs import basicNodeType, latentNodeType
from src.selection_bias.classes.selection_bias import selectionBiasNodeType
from src.transportability.classes.transportability import transportabilityNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation
from src.inference.adjustment.ST_adjustment import STAdjustment, STAdjustmentName
from src.inference.classes.trace import Trace
from src.inference.classes.failure import Failure

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.compute.compute_utils import ComputeUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.transportability_utils import TransportabilityUtils
 

alg_name = 'ST'

st_base = 0
st_sum_over = 1
st_transport = 2
st_selection_bias = 3


class STEngine(BaseEngine):

    # private populations: Population[];
    # private experimentSpecs: ExperimentSpecs;
    # private observationSpecs: ObservationSpecs;
    # private latentNodes: Node[];
    # private latentNodeNames: string[];

    def __init__(self):
        super().__init__()

        # self.P = None
        self.populations = []
        self.experimentSpecs = {}
        self.observationSpecs = {}
        self.latentNodes = []
        self.latentNodeNames = []
 

    # CausalQuery, Graph, EngineConfiguration
    # bool
    def canCompute(self, query, G, config = {}):
        if not query or not G:
            return False

        nonBasicNodes = su.difference(G.nodes, gu.filterBasicNodes(G.nodes, False), 'name')
        unsupportedNodes = list(filter(lambda n: n['type_'] != selectionBiasNodeType.id_ and n['type_'] != transportabilityNodeType.id_, nonBasicNodes))
        
        if len(unsupportedNodes) > 0:
            return False

        return True


    # Expression | Failure<Any>
    def compute(self, query, G, config = None):
        self.populations = config['populations'] if config is not None and 'populations' in config else [targetPopulation]
        self.experimentSpecs = config['experimentSpecs'] if config is not None and 'experimentSpecs' in config else {}
        self.observationSpecs = config['observationSpecs'] if config is not None and 'observationSpecs' in config else {}
        
        self.clearTrace()

        # implement projectOverNonLatentNodes
        # graph = pu.projectOverNonLatentNodes(G)
        graph = G
        self.currentQuery = query
        self.latentNodes = list(filter(lambda n: n['type_'] == latentNodeType.id_, graph.nodes))
        self.latentNodeNames = list(map(lambda n: n['name'], self.latentNodes))

        [y, z, x] = self.normalizeQuery(query, graph)

        conditional = z is not None and not su.isEmpty(z)

        if conditional:
            return self.createFailureMessage()

        # 2 = 1 source and a target population
        if len(self.populations) != 2:
            return self.createFailureMessage()

        # ? target distribution cannot be experimental
        targetExpCollection = self.experimentSpecs[targetPopulation.label]
        targetExps = targetExpCollection[0]

        if len(targetExps) > 0:
            return self.createFailureMessage()

        # experiments on x should be available in source population
        sourcePops = list(filter(lambda p: p.label != targetPopulation.label, self.populations))
        sourcePop = sourcePops[0]
        sourceExpCollection = self.experimentSpecs[sourcePop.label]
        sourceExps = sourceExpCollection[0]

        if not su.equals(query.x, sourceExps, 'name'):
            return self.createFailureMessage()

        V = gu.filterBasicNodes(graph.nodes)
        V = sorted(V, key = lambda n: n['name'])

        W = self.observationSpecs[targetPopulation.label] if targetPopulation.label in self.observationSpecs else V
        W = su.difference(W, su.union(x, y, 'name'), 'name')
        W = su.difference(W, targetExps, 'name')

        adjustment = STAdjustment.findAdjustment(graph, x, y, W, sourcePop)

        if adjustment is None:
            return self.createFailureMessage()

        resultExp = adjustment['expression']

        sourcePopulation = self.populations[1]

        Z = adjustment['covariates']
        emptySet = len(Z) == 0

        S = cu.getSelectionBiasNode(graph)
        Si = TransportabilityUtils.getSelectionNodesFor(G, sourcePopulation)

        trExp = eu.create('sum', [Z, None, eu.create('product', [
            eu.create('prob', [y, Z, x, sourcePopulation.label]),
            eu.create('prob', [Z, None, None, targetPopulation.label])
        ])])
        sExp = resultExp

        sTrace = Trace()
        sTrace.query = sExp
        sTrace.result = None
        sTrace.algorithmInfo = {
            'algName': alg_name, 'line': st_selection_bias, 'args': {
                'indep': eu.create('indep', [y, S, su.union(x, Z, 'name'), eu.create('concat', ['G_{\\overline{', x, '}}'])]),
                'domain': sourcePopulation.label,
                'domains': [sourcePopulation.label]
            }
        }
        sTrace.subgraph = { 'V': su.union(gu.nodeToList(graph.nodes), self.latentNodeNames), 'over': gu.nodeToList(x) }

        siNodesExp = eu.create('script', ['S', sourcePopulation.label]) if len(Si) > 0 else { 'name': '\\emptyset', 'type_': basicNodeType.id_ }

        trTrace = Trace()
        trTrace.query = trExp
        trTrace.result = None
        trTrace.algorithmInfo = {
            'algName': alg_name, 'line': st_transport, 'args': {
                'indep': eu.create('indep', [y, siNodesExp, su.union(x, Z, 'name'), eu.create('concat', ['G_{\\overline{', x, '}}'])]),
                'domain': sourcePopulation.label,
                'domains': [sourcePopulation.label]
            }
        }
        trTrace.subgraph = { 'V': su.union(gu.nodeToList(G.nodes), self.latentNodeNames), 'over': gu.nodeToList(x) }
        trTrace.children = [sTrace]

        rootTrace = Trace()

        if emptySet:
            rootTrace.query = eu.create('prob', [y, None, x, targetPopulation.label])
            rootTrace.result = resultExp
            rootTrace.algorithmInfo = {
                'algName': alg_name, 'line': st_base, 'args': {
                    'populations': self.populations,
                    'experiments': self.experimentSpecs,
                    'W': W
                }
            }
            rootTrace.children = [trTrace]
            rootTrace.simplification = eu.create('text', ['Obtained by an empty admissible set'])
        else:
            sumoverExp = eu.create('sum', [Z, None, eu.create('product', [
                eu.create('prob', [y, Z, x, targetPopulation.label]),
                eu.create('prob', [Z, None, None, targetPopulation.label])
            ])])

            sumoverTrace = Trace()
            sumoverTrace.query = sumoverExp
            sumoverTrace.result = None
            sumoverTrace.algorithmInfo = {
                'algName': alg_name, 'line': st_sum_over, 'args': {
                    'S': Z
                }
            }
            sumoverTrace.children = [trTrace]

            rootTrace.query = eu.create('prob', [y, None, x, targetPopulation.label])
            rootTrace.result = resultExp
            rootTrace.algorithmInfo = {
                'algName': alg_name, 'line': st_base, 'args': {
                    'populations': self.populations,
                    'experiments': self.experimentSpecs,
                    'W': W
                }
            }
            rootTrace.children = [sumoverTrace]
            rootTrace.simplification = eu.create('text', ['Obtained by ' + adjustment['name'] + ' with an admissible set ', '$' if emptySet else '$\\lbrace', '\\emptyset' if emptySet else adjustment['covariates'], '$' if emptySet else '\\rbrace$'])

        self.pushTrace(rootTrace)
        self.numberTrace(rootTrace)

        return resultExp


    # Dict[str, AlgorithmTracer]
    def getAlgorithmTracers(self):
        return {
            # 'ST': STAlgorithmTracer()
            'ST': None
        }


    # Failure<Any>
    def createFailureMessage(self):
        failureExp = eu.create('concat', [
            eu.create('text', ['The identifiability of ']),
            eu.create('prob', [self.currentQuery.y, self.currentQuery.z, self.currentQuery.x, targetPopulation.label]),
            eu.create('text', [' cannot be determined.'])
        ])

        return Failure(failureExp, None)