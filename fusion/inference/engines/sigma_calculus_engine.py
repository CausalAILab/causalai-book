import functools

from src.graph.classes.graph_defs import latentNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation, transportabilityNodeType
from src.intervention.classes.intervention import interventionNodeType
from src.inference.classes.failure import Failure
from src.inference.utils.graph_utils import compareNames, sortByName

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils
from src.graph_analysis.sigma_calculus.sigma_calculus_utils import SigmaCalculusUtils as scu
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.compute.compute_utils import ComputeUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.transportability_utils import TransportabilityUtils
from src.inference.utils.confounding_analysis import ConfoundingAnalysis


alg_name = 'sigma-calc'

op_sum_anc = 1
op_c_decomp = 2
op_transp = 3

docalc_base = 0
docalc_rule3 = 1
docalc_rule2 = 4
# docalc_rule3_old = 5
docalc_sum_over = 2
docalc_factorize = 3
docalc_cond_prob = 6
docalc_c_comp_form = 7
docalc_subgoal = 8
docalc_comp_num = 9
docalc_comp_den = 10
docalc_comp_factor = 11
docalc_transport = 12
docalc_same_domain_exp = 13
docalc_c_comp = 14

factor_fraction = 0
factor_terminal = 1
factor_subgoal = 2


class SigmaCalculusEngine(BaseEngine):

    # private populations: Population[];
    # private experiments: Node[][][];
    # private experimentSpecs: ExperimentSpecs;
    # private selectionDiagram: Graph;
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
        # self.experimentSpecs = {}
        self.interventions = []
        self.interventionSpecs = {}

    # CausalQuery, Graph, EngineConfiguration
    # boolean

    def canCompute(self, query, G, config=None):
        if not query or not G:
            return False

        nonBasicNodes = su.difference(
            G.nodes, gu.filterBasicNodes(G.nodes, False), 'name')
        unsupportedNodes = list(filter(
            lambda n: n['type_'] != transportabilityNodeType.id_ and n['type_'] != interventionNodeType.id_, nonBasicNodes))

        if len(unsupportedNodes) > 0:
            if len(unsupportedNodes) == 1:
                S = cu.getSelectionBiasNode(G)

                if S is not None and not cu.inSBContext(G):
                    return True

            return False

        return True

    # Expression | Failure<Any>

    def compute(self, query, G, config=None):
        self.populations = config['populations'] if config is not None and 'populations' in config else [
            targetPopulation]
        self.interventions = config['interventions'] if config is not None and 'interventions' in config else [
        ]
        self.interventionSpecs = config['interventionSpecs'] if config is not None and 'interventionSpecs' in config else {
        }

        self.clearTrace()

        graph = ProjectionUtils.projectOverNonLatentNodes(G)

        # save original graph before removing metadata and others
        self.selectionDiagram = graph
        self.originalGraph = graph = self.simplifyGraph(graph)
        self.latentNodes = list(
            filter(lambda n: n['type_'] == latentNodeType.id_, graph.nodes))
        self.latentNodeNames = list(map(lambda n: n['name'], self.latentNodes))

        self.currentQuery = query

        # [y, w, x, intvs] = self.normalizeQuery(query, graph)
        normalizedQuery = self.normalizeQuery(query, graph)

        y = normalizedQuery[0]
        w = normalizedQuery[1]
        x = normalizedQuery[2]
        intvs = []

        if len(normalizedQuery) == 4:
            intvs = normalizedQuery[3]

        self.V = sorted(graph.nodes, key=sortByName)
        self.P = self.setScripts(
            eu.create('prob', [gu.nodesToVariables(self.V)]), 0, None)

        # try:
        self.popTrace()

        result = self.identify(y, x, w, intvs, self.P, graph)
        result = pu.simplify(result)

        if config is not None and 'renameReinstantiatedVariables' in config and config['renameReinstantiatedVariables'] == True:
            self.distinguishVariables(result, self.replaceVariables)

        return result
        # except Exception as error:
        #     if self.getTrace() is not None:
        #         self.getTrace().result = error

        # return error

    # Node[], Node[], Node[], Intervention[], Expression, Graph
    # Expression

    def identify(self, y, x, w, intvs, P, G):
        # Step 1
        V = gu.topoSort(G, True)
        V = gu.filterBasicNodes(V)
        self.V = V

        GsigmaX = scu.createGraphSigma(G, intvs)
        D = gu.ancestors(su.union(y, w, 'name'), gu.subgraph(GsigmaX, V))

        G_D = gu.subgraph(G, D)
        G_D_Wbar = gu.transform(G_D, None, w)
        GsigmaX_Wbar_D = scu.createGraphSigma(G_D_Wbar, intvs)
        reachableFromY = gu.reach(y, gu.subgraph(GsigmaX_Wbar_D, V))
        reachableNodeNames = list(map(lambda n: n['name'], reachableFromY))
        Wy = list(filter(lambda n: n['name'] in reachableNodeNames, w))
        # WyComp = su.difference(w, Wy, 'name')
        # Wy = list(filter(lambda n: not DSeparation.test(Gsigma_D_Wbar, y, n, None), w))

        GWbar = gu.transform(G, None, w)
        GsigmaXWbar = scu.createGraphSigma(GWbar, intvs)
        A = gu.ancestors(su.union(y, Wy, 'name'), gu.subgraph(GsigmaXWbar, V))

        G_A = gu.subgraph(G, A)
        GsigmaX_A = scu.createGraphSigma(G_A, intvs)
        CG_A = gu.cCompDecomposition(GsigmaX_A, True)
        # filter out all non-basic nodes
        CG_A = list(filter(lambda C: len(
            su.intersection(C, V, 'name')) == len(C), CG_A))

        AmYW = su.difference(A, su.union(y, w, 'name'), 'name')
        AmW = su.difference(A, w, 'name')
        AwithoutX = list(filter(lambda Ai: len(
            su.intersection(Ai, x, 'name')) == 0, CG_A))

        factors = []

        domains = self.populations
        Zcollection = self.interventions

        for Ai in AwithoutX:
            solved = False

            # do we pick one domain, or multiple ones and assign weight?
            # foreach domain i s.t. Ai cap delta_i = emptyset
            for i in range(len(domains)):
                if solved:
                    break

                Si = TransportabilityUtils.getSelectionNodesFor(
                    self.selectionDiagram, domains[i])
                deltaTargets = gu.children(Si, G)

                # compare Ai with nodes pointed by Si
                if len(su.intersection(Ai, deltaTargets, 'name')) > 0:
                    continue

                # assume 1 distribution from a collection of dists
                # foreach sigma_Z in Z^i s.t. Ai cap Z = emptyset
                Zi = Zcollection[i]

                for Zintvs in Zi:
                    if solved:
                        break

                    Z = []

                    for intv in Zintvs:
                        Z = su.union(Z, intv.target, 'name')

                    if len(su.intersection(Ai, Z, 'name')) > 0:
                        continue

                    GsigmaZ = scu.createGraphSigma(G, Zintvs)
                    CG_Z = gu.cCompDecomposition(GsigmaZ, True)
                    # filter out all non-basic nodes
                    CG_Z = list(filter(lambda C: len(
                        su.intersection(C, V, 'name')) == len(C), CG_Z))

                    Bi = None

                    for Bk in CG_Z:
                        if su.isSubset(Ai, Bk, 'name'):
                            Bi = Bk
                            break

                    if Bi is None:
                        continue

                    # compute Q^k[Bi; sigmaZ] from Q^k[V; sigmaZ]
                    # compute Q[Ai; sigmaX] from Q^k[Bi; sigmaZ]
                    sigmaList = self.createIntervenedNodeList(Zintvs)
                    PvSigmaZ = self.createPExpression(
                        V, [], [], i, [], sigmaList)

                    QBi = ConfoundingAnalysis.qComputeCComp(Bi, V, PvSigmaZ)
                    GsigmaZ_Bi = gu.subgraph(GsigmaZ, Bi)
                    QAi = self.qIdentify(Ai, Bi, QBi, GsigmaZ_Bi)

                    if QAi is not None:
                        solved = True
                        factors.append(QAi)
                        break

            if not solved:
                raise self.createFailureMessage(G)

        # QAi = replace(Ai, sigmaX)
        # rewrite pu s.t. it writes P(..; sigmaX) part
        AwithX = list(filter(lambda Ai: len(
            su.intersection(Ai, x, 'name')) > 0, CG_A))

        for Ai in AwithX:
            AiParents = gu.parents(Ai, gu.subgraph(G, V))
            AiParents = su.difference(AiParents, Ai, 'name')
            sigmaList = self.createIntervenedNodeList(intvs)
            exp = self.createPExpression(
                Ai, AiParents, None, 0, [], sigmaList)
            factors.append(exp)

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
        prodFactors = eu.create('product', factors)
        num = pu.sumOver(ou.clone(prodFactors), AmYW)
        den = pu.sumOver(ou.clone(prodFactors), AmW)

        return eu.create('frac', [num, den])

    def qIdentify(self, C, T, Q, G):
        A = su.intersection(gu.ancestors(C, gu.subgraph(G, T)), T, 'name')

        if su.equals(A, C):
            return pu.sumOver(ou.clone(Q), su.difference(T, C, 'name'))
        elif su.equals(A, T):
            return None
        else:
            QA = pu.sumOver(ou.clone(Q), su.difference(T, A, 'name'))
            G_A = gu.subgraph(G, A)
            CG_A = gu.cCompDecomposition(G_A)

            for Tip in CG_A:
                if su.isSubset(C, Tip, 'name'):
                    Ti = su.intersection(Tip, A, 'name')
                    QTi = ConfoundingAnalysis.qComputeCComp(
                        Ti, su.intersection(self.V, A, 'name'), QA)
                    G_Ti = gu.subgraph(G, Ti)

                    # should it be the same graph or the subgraph?
                    return self.qIdentify(C, Ti, QTi, G_Ti)

    def createPExpression(self, scope, conditional=[], atomic_intervention=[], domain=0, experiments=[], interventions=[]):
        return self.setScripts(eu.create('prob', [
            scope,
            su.difference(conditional, experiments, 'name'),
            atomic_intervention,
            None,
            interventions
        ]), domain, experiments)

    def setScripts(self, P, domain, experiments):
        return TransportabilityUtils.setScripts(P, experiments, self.populations[domain] if self.populations is not None and len(self.populations) > 1 else None)

    # Intervention[]
    #
    # sigma_AB, sigma^1_C: output [[A,B],[]] and [[C],[]]
    # 1st entry: list of node/strings for subscript
    # 2nd entry: list of node/strings for superscript
    def createIntervenedNodeList(self, intvs):
        if intvs is None or len(intvs) == 0:
            return []

        expList = []

        # group sigma nodes by each population
        for i in range(len(self.populations)):
            pop = self.populations[i]

            intvsInDomain = list(filter(
                lambda intv: intv.node is not None and 'metadata' in intv.node and 'populations' in intv.node['metadata'] and pop.id_ in intv.node['metadata']['populations'], intvs))

            targetsInDomain = list(
                map(lambda intv: intv.target, intvsInDomain))
            nodeNames = list(map(lambda n: n['name'], targetsInDomain))

            if len(targetsInDomain) == 0:
                continue

            expListEntry = [nodeNames, [pop.id_]]
            expList.append(expListEntry)

        return expList

    # rewrite
    def createFailureMessage(self, witness):
        queryExpression = self.getQueryExpression(
            self.currentQuery.x, self.currentQuery.y, self.currentQuery.z)

        if len(self.populations) > 1:
            queryExpression.parts.append('\\*')

        failureExp = [
            queryExpression,
            eu.create('text', [' is not transportable from ' if len(
                self.populations) > 1 else ' is not identifiable from '])
        ]

        return Failure(eu.create('concat', failureExp), witness)

    def getQueryExpression(self, X, Y, Z):
        return eu.create('prob', [Y, Z, X])

    def getAlgorithmTracers(self):
        return {
            # 'sigma-calc': new SigmaCalculusAlgorithmTracer()
            'sigma-calc': None
        }
