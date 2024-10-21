import functools

from src.graph.classes.graph_defs import latentNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation, transportabilityNodeType
from src.inference.adjustment.backdoor_adjustment import BackdoorAdjustment
from src.inference.adjustment.frontdoor_adjustment import FrontdoorAdjustment
from src.inference.classes.trace import Trace
from src.inference.classes.failure import Failure
from src.path_analysis.d_separation import DSeparation
from src.inference.utils.graph_utils import sortByName, compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.compute.compute_utils import ComputeUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.transportability_utils import TransportabilityUtils


alg_name = 'do-calc'

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


class DoCalculusEngine(BaseEngine):

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
        self.latentNodes = []
        self.latentNodeNames = []
        self.originalGraph = None
        self.selectionDiagram = None
        self.populations = []
        self.experiments = None
        self.experimentSpecs = {}

    # CausalQuery, Graph, EngineConfiguration
    # boolean

    def canCompute(self, query, G, config=None):
        if not query or not G:
            return False

        nonBasicNodes = su.difference(
            G.nodes, gu.filterBasicNodes(G.nodes, False), 'name')
        unsupportedNodes = list(
            filter(lambda n: n['type_'] != transportabilityNodeType.id_, nonBasicNodes))

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
        self.experiments = config['experiments'] if config is not None and 'experiments' in config else [
        ]
        self.experimentSpecs = config['experimentSpecs'] if config is not None and 'experimentSpecs' in config else {
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

        [y, z, x] = self.normalizeQuery(query, graph)

        V = sorted(graph.nodes, key=sortByName)
        self.P = self.setScripts(
            eu.create('prob', [gu.nodesToVariables(V)]), 0, None)

        try:
            newTrace = Trace()
            newTrace.query = self.createPExpression(y, z, x, 0, None)
            newTrace.result = None
            newTrace.subgraph = su.union(
                gu.nodeToList(graph.nodes), self.latentNodeNames)
            newTrace.algorithmInfo = {
                'algName': alg_name,
                'args': {
                    'populations': ou.clone(self.populations),
                    'experiments': ou.clone(self.experimentSpecs)
                },
                'line': docalc_base
            }

            trace = self.pushTrace(newTrace)

            targetExpCollection = self.experimentSpecs[targetPopulation.label]
            observationExists = su.belongs(
                [], targetExpCollection) if targetExpCollection is not None else False

            # try a simple derivation first
            result = self.trySimpleDerivation(y, x, z, self.P, graph)

            # run the full algorithm if a simple derivation is not enough
            if result is None or (result is not None and not observationExists):
                result = self.identifyCond(y, x, z, self.P, graph)
                result = pu.simplify(result)

                # look for an adjustment if the simplification is on
                adjustment = None

                if config is not None and 'simplifyWhenPossible' in config and config['simplifyWhenPossible'] == True:
                    adjustment = BackdoorAdjustment.findAdjustment(
                        graph, x, y, z, self.P)

                    # try front-door adjustment
                    conditional = z is not None and not su.isEmpty(z)

                    if adjustment is None and not conditional:
                        adjustment = FrontdoorAdjustment.findAdjustment(
                            graph, x, y, self.P)

                if adjustment is not None:
                    emptySet = 'covariates' in adjustment and len(
                        adjustment['covariates']) == 0
                    self.getTrace().simplification = eu.create('text', ['Obtained by ' + adjustment['name'] + ' with an admissible set ',
                                                                        '$' if emptySet else '$\\lbrace', '\\varnothing' if emptySet else adjustment['covariates'], '$' if emptySet else '\\rbrace$'])
                    trace.algorithmInfo['args']['adjustment'] = {
                        'set': adjustment['covariates']
                    }
                    trace.algorithmInfo['args']['adjustment_name'] = adjustment['name']

                    result = adjustment['expression']

                # implement
                # surrogateAdjustment = SurrogateAdjustment.findAdjustment(graph, x, y, self.P)

                # if surrogateAdjustment is not None:
                #     trace.algorithmInfo['args']['adjustment'] = {
                #         'W': surrogateAdjustment['W'],
                #         'R': surrogateAdjustment['R']
                #     }
                #     trace.algorithmInfo['args']['adjustment_name'] = surrogateAdjustment['name']

            if config is not None and 'renameReinstantiatedVariables' in config and config['renameReinstantiatedVariables'] == True:
                self.distinguishVariables(result, self.replaceVariables)

            trace.result = result
            self.numberTrace(trace)

            return result
        except Exception as error:
            if self.getTrace() is not None:
                self.getTrace().result = error

            return error

    # Try rule 2 or rule 3 to check if the effect is identifiable.
    # Node[], Node[], Node[], Expression, Graph
    # Expression

    def trySimpleDerivation(self, y, x, z, P, G):
        xNAnZ = su.difference(x, gu.ancestors(z, G), 'name')

        if DSeparation.test(gu.transform(G, xNAnZ, None), x, y, z):
            result = self.createPExpression(y, z)

            trace = Trace()
            trace.query = result
            trace.result = result
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_rule3, 'args': {
                    'indeps': [
                        eu.create('indep', [x, y, z, eu.create(
                            'concat', ['G_{\\overline{', x, '}}'])])
                    ]
                }
            }
            trace.subgraph = {'V': su.union(gu.nodeToList(
                G.nodes), self.latentNodeNames), 'over': gu.nodeToList(x)}

            self.pushTrace(trace)
            self.popTrace()

            return result

        if DSeparation.test(gu.transform(G, None, x), x, y, z):
            result = self.createPExpression(y, su.union(x, z, 'name'))

            trace = Trace()
            trace.query = result
            trace.result = result
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_rule2, 'args': {
                    'indeps': [
                        eu.create('indep', [x, y, z, eu.create(
                            'concat', ['G_{\\underline{', x, '}}'])])
                    ]
                }
            }
            trace.subgraph = {'V': su.union(gu.nodeToList(
                G.nodes), self.latentNodeNames), 'under': gu.nodeToList(x)}

            self.pushTrace(trace)
            self.popTrace()

            return result

        return None


    # Node[], Node[], Node[], Expression, Graph
    # Expression

    def identifyCond(self, y, x, z, P, G):
        # if there is no conditional part then use identify directly
        if z is None or su.isEmpty(z):
            return self.identify(y, x, P, G)

        originalX = x
        originalZ = z

        # find a maximal set for which we can apply rule 2

        # do while
        while True:
            hasRemovedZ = False

            for varZ in z:
                zMVarZ = su.difference(z, [varZ], 'name')

                if DSeparation.test(gu.transform(G, x, [varZ]), y, [varZ], su.union(x, zMVarZ, 'name')):
                    hasRemovedZ = True
                    x = su.union(x, [varZ])
                    z = zMVarZ
                    break

            if not hasRemovedZ or su.isEmpty(z):
                break

        removedZ = su.difference(originalZ, z, 'name')

        if not su.isEmpty(removedZ):
            # add trace with application of rule 2
            trace = Trace()
            trace.query = self.getQueryExpression(x, y, z)
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_rule2, 'args': {
                    'indeps': [
                        eu.create('indep', [
                            sorted(removedZ, key=sortByName),
                            sorted(y, key=sortByName),
                            sorted(su.union(originalX, z, 'name'),
                                   key=sortByName),
                            eu.create('concat', ['G_{\\overline{', sorted(
                                originalX, key=sortByName), '}\\underline{', sorted(removedZ, key=sortByName), '}}'])
                        ])
                    ]
                }
            }
            trace.subgraph = {
                'V': sorted(su.union(gu.nodeToList(G.nodes), self.latentNodeNames)),
                'over': sorted(gu.nodeToList(originalX)),
                'under': sorted(gu.nodeToList(removedZ))
            }

            self.pushTrace(trace)

        if not su.isEmpty(z):
            yz = sorted(su.union(y, z, 'name'), key=sortByName)

            # add trace breaking the effect into two subgoals
            if len(self.experiments) > 0:
                numExp = self.createPExpression(yz, [], x)
                denExp = self.createPExpression(z, [], x)
            else:
                numExp = eu.create('prob', [yz, None, x])
                denExp = eu.create('prob', [z, None, x])

            trace = Trace()
            trace.query = eu.create('frac', [numExp, denExp])
            trace.result = None
            trace.algorithmInfo = {'algName': alg_name,
                                   'line': docalc_cond_prob, 'args': {}}
            trace.subgraph = sorted(
                su.union(gu.nodeToList(G.nodes), self.latentNodeNames))

            self.pushTrace(trace)

        Pp = self.identify(su.union(y, z, 'name'), x, P, G)

        if not su.isEmpty(z):
            self.popTrace()

        if not su.isEmpty(removedZ):
            self.popTrace()

        return eu.create('frac', [Pp, pu.sumOver(ou.clone(Pp), y)])

    # Node[], Node[], Expression, Graph
    # Expression

    def identify(self, y, x, P, G):
        V = gu.topoSort(G, True)
        V = gu.filterBasicNodes(V)

        Xp = su.difference(V, x, 'name')
        D = gu.ancestors(y, gu.subgraph(G, Xp))
        G_D = gu.subgraph(G, D)
        CG_D = gu.cCompDecomposition(G_D, True)
        nCG_D = len(CG_D)
        DmY = su.difference(D, y, 'name')
        queryFactors = []
        factors = []

        Pv = self.createPExpression(sorted(D, key=sortByName), [], sorted(
            su.difference(V, D, 'name'), key=sortByName), 0, [])
        # Pv = self.createPExpression(sorted(D, key = lambda n: n['name']), None, sorted(su.difference(V, D, 'name'), key = lambda n: n['name']), 0, None)

        # get the variables that are ancestors of Y only through X
        AnYMD = su.difference(su.intersection(
            gu.ancestors(y, G), V, 'name'), D, 'name')

        # remove X from the previous set
        AnYMDX = su.difference(AnYMD, x, 'name')

        # rule 3 to add ancestors of Y only through X to the intervention
        if not su.isEmpty(AnYMDX):
            trace = Trace()
            trace.query = self.createPExpression(y, [], AnYMD)
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_rule3, 'args': {
                    'indeps': [
                        eu.create('indep', [
                            sorted(AnYMDX, key=sortByName), sorted(
                                y, key=sortByName), sorted(x, key=sortByName),
                            eu.create(
                                'concat', ['G_{\\overline{', sorted(AnYMD, key=sortByName), '}}'])
                        ])
                    ]
                }
            }
            trace.subgraph = {'V': su.union(gu.nodeToList(
                V), self.latentNodeNames), 'over': gu.nodeToList(AnYMD)}

            self.pushTrace(trace)

        # trace that specifies the required sum
        if not su.isEmpty(DmY):
            trace = Trace()
            trace.query = eu.create(
                'sum', [sorted(DmY, key=sortByName), None, Pv])
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_sum_over, 'args': {
                    'S': sorted(DmY, key=sortByName)
                }
            }
            trace.subgraph = sorted(
                su.union(gu.nodeToList(G.nodes), self.latentNodeNames))

            self.pushTrace(trace)

        # c-component decomposition trace
        if nCG_D > 1:
            trace = Trace()
            trace.query = None
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_c_comp_form, 'args': {
                    'numCComps': nCG_D,
                    'cComponents': CG_D,
                    'factors': queryFactors,
                    'Pv': Pv
                }
            }

            self.pushTrace(trace)

        # go over each c-component in reverse order
        for Di in CG_D:
            queryFactors.append(self.createPExpression(sorted(Di, key=sortByName), [
            ], sorted(su.difference(V, Di, 'name'), key=sortByName), 0, []))

            # if there is more than one c-component create a trace for a new branch in the tree
            if nCG_D > 1:
                trace = Trace()
                trace.query = queryFactors[len(queryFactors) - 1]
                trace.result = None
                trace.algorithmInfo = {
                    'algName': alg_name, 'line': docalc_c_comp, 'args': {}}
                trace.subgraph = sorted(
                    su.union(gu.nodeToList(V), self.latentNodeNames))

                self.pushTrace(trace)

            fExp = self.qIdentify(Di, V, G)

            # if there is more than one c-component we need to pop the previously created trace
            if nCG_D > 1:
                self.popTrace().result = fExp

            factors.append(fExp)

        # if there was more than one c-component or there were variables added a trace was created, pop that trace
        if nCG_D > 1:
            self.popTrace().query = eu.create('sum', [sorted(DmY, key=sortByName), None, eu.create(
                'product', queryFactors)]) if not su.isEmpty(DmY) else eu.create('product', queryFactors)

        # if there was a sum, pop that trace
        if not su.isEmpty(DmY):
            self.popTrace()

        # if there were variables added to the intervention, pop that trace
        if not su.isEmpty(AnYMDX):
            self.popTrace()

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

        return pu.sumOver(eu.create('product', factors), DmY)

    # /**
    #  * Identifies the distribution Q[C] from P(v)=Q[V] in the graph G
    #  * @param C A set of variables such that C \subset T and G_C has a single c-component
    #  * @param V The set of observable variables ordered topologically according to G
    #  * @param G A graph over the variables in V
    #  * @returns An expression for Q[C] in terms of P(v)
    #  */

    def qIdentify(self, C, V, G):
        steps = list(reversed(self.derive(C, V, G)))
        return self.unroll(C, V, steps, G)

    # /**
    #  * Derives a expression for P_{v \ c}(c) in terms of P_{v \ t}(t)
    #  * @param C A set of variables such that C \subset T and G_C has a single c-component
    #  * @param T A set of variables ordered topologically according to G
    #  * @param G A graph over the variables in T
    #  * @param tryTransport Determines if the derivation should attempt to perform transportability
    #  * @returns The derivation steps required to compute Q[C] from Q[T]
    #  */

    def derive(self, C, T, G, tryTransport = True):
        if su.equals(C, T, 'name'):
            if tryTransport:
                return self.tryTransport(C, T, G)

            return []

        # alter order such that ancestors(C) < non-ancestors(C) in T
        Tanc = su.intersection(T, gu.ancestors(C, G), 'name')

        def sortByAncestry(a, b):
            aIn = su.belongs(a, Tanc, compareNames)
            bIn = su.belongs(b, Tanc, compareNames)

            if aIn and not bIn:
                return -1
            elif not aIn and bIn:
                return 1
            else:
                return 0

        T = sorted(T, key = functools.cmp_to_key(sortByAncestry))

        A = su.intersection(T, gu.ancestors(C, G), 'name')

        # sum out T \ A (non-ancestors of C)
        if not su.equals(A, T, 'name'):
            order = self.derive(C, A, gu.subgraph(G, A), tryTransport)

            if order is None:
                return []
            
            order.append({ 'T': T, 'op': op_sum_anc })
            
            return order
        else:
            # c-component decomposition
            CG_T = gu.cCompDecomposition(gu.subgraph(G, T), True)

            if len(CG_T) == 1:
                if tryTransport:
                    return self.tryTransport(C, T, G)
                else:
                    raise self.createFailureMessage(G)

            for Tip in CG_T:
                if su.isSubset(C, Tip, 'name'):
                    # the following intersection will assign the same elements
                    # to Tip but in the order defined by T
                    Tip_cf = su.intersection(T, Tip, 'name')
                    order = self.derive(C, Tip_cf, gu.subgraph(G, Tip_cf), tryTransport)
                    
                    if order is None:
                        return []
                    
                    order.append({ 'T': T, 'op': op_c_decomp })

                    return order


    # Node[], Node[], Graph
    # DerivationStep[]

    def tryTransport(self, C, T, G):
        domains = self.populations
        Zs = self.experiments
        E = []
        X = su.difference(T, C, 'name')

        for i in range(len(domains)):
            Zcollection = Zs[i]

            for Z in Zcollection:
                ZCapT = su.intersection(Z, T, 'name')

                if not su.isSubset(ZCapT, X, 'name'):
                    continue

                try:
                    Tp = su.difference(T, Z, 'name')
                    GminusZcapX = gu.subgraph(self.originalGraph, su.difference(self.originalGraph.nodes, Z, 'name'))
                    newT = gu.topoSort(GminusZcapX, True)
                    newT = gu.filterBasicNodes(newT)
                    order = self.derive(C, newT, GminusZcapX, False)
                    
                    if order is not None:
                        E.append({ 'T': Tp, 'domain': 0, 'experiments': Z, 'steps': list(reversed(order)) })
                except:
                    pass

        if len(E) > 0:
            return [{ 'T': T, 'op': op_transp, 'transportabilityInfo': E }]

        raise self.createFailureMessage(G)

    # Node[], Node[], DerivationStep[], Graph, number, Node[]
    # Expression

    def unroll(self, W, V, rSteps, G, domain=0, experiments=None):
        step = None

        if len(rSteps) > 0:
            step = rSteps.pop()

        VmW = su.difference(V, W, 'name')
        VmWmExp = su.difference(VmW, experiments, 'name')

        if step is None and su.isEmpty(VmWmExp):
            return self.createPExpression(V, [], [], domain, experiments)
        elif step is None:
            raise self.createFailureMessage(G)

        if step['op'] == op_sum_anc:
            return self.unrollSumAnc(step, W, V, rSteps, G, domain, experiments)
        elif step['op'] == op_c_decomp:
            return self.unrollCDecomp(step, W, V, VmW, rSteps, G, domain, experiments)
        elif step['op'] == op_transp:
            return self.unrollTransp(step, W, V, VmW, rSteps, G, domain, experiments)
        else:
            raise self.createFailureMessage(
                'Unknown derivation operation: ' + step['op'])

    # DerivationStep, Node[], Node[], DerivationStep[], Graph, number, Node[]
    # Expression

    def unrollSumAnc(self, step, W, V, rSteps, G, domain=0, experiments=None):
        # variables to sum over
        TmW = su.difference(step['T'], W, 'name')
        intervention = su.difference(V, step['T'], 'name')
        overlineVars = su.difference(V, W, 'name')

        expNames = list(
            map(lambda n: n['name'], experiments)) if experiments is not None else []

        # a trace that removes the variables (that will be summed over) from the do in the result expression
        trace = Trace()
        trace.query = self.createPExpression(sorted(W, key=sortByName), [], sorted(
            intervention, key=sortByName), domain, experiments)
        trace.result = None
        trace.algorithmInfo = {
            'algName': alg_name, 'line': docalc_rule3, 'args': {
                'indep': eu.create('indep', [
                    sorted(TmW, key=sortByName),
                    sorted(W, key=sortByName),
                    sorted(su.union(intervention, experiments, 'name'),
                           key=sortByName),
                    eu.create('concat', ['G_{\\overline{', sorted(
                        su.union(overlineVars, experiments, 'name'), key=sortByName), '}}'])
                ])
            }
        }
        trace.subgraph = {
            'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
            'over': sorted(su.union(gu.nodeToList(overlineVars), expNames))
        }

        self.pushTrace(trace)

        if not su.isEmpty(intervention):
            # sum over trace
            trace = Trace()
            trace.query = eu.create('sum', [
                sorted(TmW, key=sortByName), None,
                self.createPExpression(sorted(step['T'], key=sortByName), [], sorted(
                    intervention, key=sortByName), domain, experiments)
            ])
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_sum_over, 'args': {
                    'S': sorted(TmW, key=sortByName)
                }
            }
            trace.subgraph = {
                'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                'over': sorted(expNames)
            }

            self.pushTrace(trace)

            # a trace indicating that the expression inside the sum will be computed
            trace = Trace()
            trace.query = self.createPExpression(sorted(su.union(W, TmW, 'name'), key=sortByName), [
            ], sorted(intervention, key=sortByName), domain, experiments)
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': docalc_subgoal, 'args': {}
            }
            trace.subgraph = {
                'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                'over': sorted(expNames)
            }

            self.pushTrace(trace)

        exp = self.unroll(step['T'], V, rSteps, G, domain, experiments)
        sumExp = pu.sumOver(exp, TmW)

        if not su.isEmpty(intervention):
            self.popTrace()
            trace = self.popTrace()
            trace.result = exp
            boundInSum = su.intersection(TmW, self.boundVariables, 'name')

            if not su.isEmpty(boundInSum):
                replaceVars = {}

                for node in boundInSum:
                    replaceVars[node['name']] = {
                        'name': node['name'],
                        'label': (node['label'] if node['label'] is not None else node['name']) + "'"
                    }

                self.replaceVariables = su.union(
                    self.replaceVariables, boundInSum, 'name')

                self.distinguishVariablesTrace(trace, replaceVars)

        self.popTrace().result = sumExp

        return sumExp

    # DerivationStep, Node[], Node[], Node[], DerivationStep[], Graph, number, Node[]
    # Expression

    def unrollCDecomp(self, step, W, V, VmW, rSteps, G, domain=0, experiments=None):
        T = su.intersection(V, step['T'], 'name')
        intervals = self.splitProbExp(W, T)
        traces = []
        lastFactors = [self.createPExpression(sorted(W, key=sortByName), [], sorted(
            VmW, key=sortByName), domain, experiments)]

        # factorization
        traces = traces + \
            self.factorize(W, T, V, VmW, intervals, domain, experiments)

        if len(traces) > 0:
            lastFactors = traces[len(traces) - 1].query.parts

        # apply rule 3
        r3result = self.rule3ToFactors(
            W, T, V, VmW, intervals, lastFactors, domain, experiments)
        traces = traces + r3result['traces']

        if r3result['factors'] is not None:
            lastFactors = r3result['factors']

        # apply rule 2
        r2result = self.rule2ToFactors(
            W, T, V, VmW, intervals, lastFactors, domain, experiments)
        traces = traces + r2result['traces']

        if r2result['factors'] is not None:
            lastFactors = r2result['factors']

        # break conditional effects
        breakCondResult = self.breakConditionals(
            T, V, VmW, intervals, domain, experiments)
        traces = traces + breakCondResult['traces']

        expNames = list(
            map(lambda n: n['name'], experiments)) if experiments is not None else []

        # actually compute the subgoals
        factors = []
        expEff = None
        i = 0
        numOfFrac = 0

        for num in breakCondResult['factorSpecs']:
            if num == factor_fraction:
                numOfFrac = numOfFrac + 1

        for interv in intervals:
            if breakCondResult['factorSpecs'][i] != factor_terminal:
                # a trace for solving multiple fractions
                if numOfFrac > 1:
                    trace = Trace()
                    trace.query = breakCondResult['factors'][i]
                    trace.result = None
                    trace.algorithmInfo = {
                        'algName': alg_name, 'line': docalc_comp_factor, 'args': {}}
                    trace.subgraph = {
                        'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                        'over': sorted(expNames)
                    }

                    self.pushTrace(trace)

                # a trace for solving the numerator
                if breakCondResult['factorSpecs'][i] == factor_fraction:
                    trace = Trace()
                    trace.query = breakCondResult['factors'][i].parts[0]
                    trace.result = None
                    trace.algorithmInfo = {
                        'algName': alg_name, 'line': docalc_comp_num, 'args': {}}
                    trace.subgraph = {
                        'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                        'over': sorted(expNames)
                    }

                    self.pushTrace(trace)

                # TODO: reuse the remaining rSteps when possible
                C = list(reversed(T[0: interv[1] + 1]))
                Vmi = V[0: V.index(T[interv[1]]) + 1]
                G_vmi = gu.subgraph(G, Vmi)
                steps = list(reversed(self.derive(C, Vmi, G_vmi)))
                expEff = self.unroll(C, Vmi, steps, G_vmi, domain, experiments)

                # denominator result = numerator result summed over certain variables
                sumOverVar = T[interv[0]: interv[1] + 1]
                denResult = pu.sumOver(ou.clone(expEff), sumOverVar)

                if breakCondResult['factorSpecs'][i] == factor_fraction:
                    self.popTrace().result = expEff

                    # a trace for solving the denominator
                    trace = Trace()
                    trace.query = breakCondResult['factors'][i].parts[1]
                    trace.result = None
                    trace.algorithmInfo = {
                        'algName': alg_name, 'line': docalc_comp_den, 'args': {'result': denResult}}
                    trace.subgraph = {
                        'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                        'over': sorted(expNames)
                    }

                    childTrace = Trace()
                    childTrace.query = None
                    childTrace.result = eu.create('sum', [
                        T[interv[0]: interv[1] + 1],
                        None,
                        breakCondResult['factors'][i].parts[0]
                    ])

                    trace.children = [childTrace]

                    self.pushTrace(trace)

                    self.popTrace()

                if numOfFrac > 1:
                    self.popTrace().result = expEff

            else:
                expEff = breakCondResult['factors'][i]

            if interv[0] > 0:
                factors.append(eu.create('frac', [
                    expEff,
                    eu.create(
                        'sum', [T[interv[0]: interv[1] + 1], None, ou.clone(expEff)])
                ]))
            else:
                factors.append(expEff)

            i = i + 1

        exp = pu.simplify(eu.create('product', factors))

        # fill the result in the other traces and pop them
        for i in range(len(traces)):
            self.popTrace().result = exp

        return exp

    # DerivationStep, Node[], Node[], Node[], DerivationStep[], Graph, number, Node[]
    # Expression

    def unrollTransp(self, step, W, V, VmW, rSteps, G, domain=0, experiments=None):
        TmW = su.difference(step['T'], W, 'name')
        intervention = su.difference(V, step['T'], 'name')
        overlineVars = su.union(intervention, TmW, 'name')
        trInfoSet = step['transportabilityInfo']
        # avoids transporting from the same domain with same experiments
        trInfoSet = su.unique(trInfoSet)
        weightedResults = []
        result = None
        j = 1

        displayTrace = len(self.populations) > 1 or (
            len(self.populations) == 1 and len(trInfoSet) > 1)

        numTransportable = 0

        for info in trInfoSet:
            if info['domain'] != domain:
                if domain == 0:
                    numTransportable = numTransportable + 1
            else:
                numTransportable = numTransportable + 1

        for info in trInfoSet:
            dLabel = self.populations[info['domain']
                                      ].label if info['domain'] is not None else ''
            expNames = list(map(
                lambda n: n['name'], info['experiments'])) if info['experiments'] is not None else []

            # Transport trace
            if info['domain'] != domain:
                if domain == 0:
                    Si = TransportabilityUtils.getSelectionNodesFor(
                        self.selectionDiagram, self.populations[info['domain']])

                    if displayTrace:
                        trace = Trace()
                        trace.query = self.createPExpression(sorted(W, key=sortByName), [], sorted(
                            VmW, key=sortByName), info['domain'], info['experiments'])
                        trace.result = None
                        trace.algorithmInfo = {
                            'algName': alg_name, 'line': docalc_transport, 'args': {
                                'indep': eu.create('indep', [
                                    sorted(W, key=sortByName),
                                    eu.create('script', ['S', dLabel]),
                                    sorted(intervention, key=sortByName),
                                    eu.create(
                                        'concat', ['G_{\\overline{', sorted(overlineVars, key=sortByName), '}}'])
                                ]),
                                'domain': dLabel,
                                'domains': list(map(lambda d: self.populations[d['domain']].label if self.populations[d['domain']] is not None else None, trInfoSet))
                            }
                        }
                        trace.subgraph = {
                            'V': sorted(su.union(su.union(su.union(gu.nodeToList(V), gu.nodeToList(Si)), self.latentNodeNames), expNames)),
                            'over': sorted(su.union(gu.nodeToList(overlineVars), expNames))
                        }

                        self.pushTrace(trace)
            else:
                if displayTrace:
                    trace = Trace()
                    trace.query = self.createPExpression(sorted(W, key=sortByName), [], sorted(
                        VmW, key=sortByName), info['domain'], info['experiments'])
                    trace.result = None
                    trace.algorithmInfo = {
                        'algName': alg_name, 'line': docalc_same_domain_exp, 'args': {
                            'experiments': info['experiments'],
                            'numPopulations': len(self.populations),
                            'domain': dLabel,
                            'domains': list(map(lambda d: self.populations[d['domain']].label if self.populations[d['domain']] is not None else None, trInfoSet))
                        }
                    }
                    trace.subgraph = {
                        'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                        'over': sorted(expNames)
                    }

                    self.pushTrace(trace)

            transportable = (info['domain'] != domain and domain == 0) or (
                info['domain'] == domain)

            if transportable:
                exp = self.unroll(W, su.difference(V, info['experiments'], 'name'), info['steps'], gu.subgraph(
                    G, su.difference(G.nodes, info['experiments'], 'name')), info['domain'], info['experiments'])

                if displayTrace:
                    self.popTrace().result = exp
                else:
                    self.getTrace().result = exp

                # bug: info.experiments adds info.experiments to intervention
                # self.setScripts(newExp, info.domain, info.experiments)
                self.setScripts(exp, info['domain'], None)

                if len(trInfoSet) == 1:
                    return exp

                if numTransportable >= 2:
                    weightedResult = eu.create('product', [eu.create(
                        'script', ['w', '' + str(j), '(' + dLabel + ')']), exp])
                    weightedResults.append(weightedResult)

                    j = j + 1
                else:
                    result = exp

        if numTransportable >= 2:
            return eu.create('()', [eu.create('+', weightedResults)])
        else:
            return result

    # Node[], Node[], Node[], Node[], number[][], number, Node[]
    # Trace[]

    def factorize(self, W, T, V, VmW, intervals, domain=0, experiments=None):
        if len(intervals) <= 1:
            return []

        factors = []
        expNames = list(
            map(lambda n: n['name'], experiments)) if experiments is not None else []

        for interv in intervals:
            factors.append(self.createPExpression(
                sorted(
                    list(reversed(T[interv[0]: interv[1] + 1])), key=sortByName),
                sorted(
                    list(reversed(su.intersection(T[0: interv[0]], W, 'name'))), key=sortByName),
                sorted(VmW, key=sortByName),
                domain, experiments
            ))

        # a trace for chain rule
        trace = Trace()
        trace.query = eu.create('product', factors)
        trace.result = None
        trace.algorithmInfo = {'algName': alg_name,
                               'line': docalc_factorize, 'args': {}}
        trace.subgraph = {
            'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
            'over': sorted(expNames)
        }

        return [self.pushTrace(trace)]

    # Node[], Node[], Node[], Node[], number[][], Expression[], number, Node[]
    # { factors: Expression[], traces: Trace[] }

    def rule3ToFactors(self, W, T, V, VmW, intervals, previousFactors, domain=0, experiments=None):
        factors = []
        traces = []
        i = 0
        expNames = list(
            map(lambda n: n['name'], experiments)) if experiments is not None else []

        for interv in intervals:
            i = i + 1
            scope = list(reversed(T[interv[0]: interv[1] + 1]))

            factors.append(self.createPExpression(
                sorted(scope, key=sortByName),
                sorted(
                    list(reversed(su.intersection(T[0: interv[0]], W, 'name'))), key=sortByName),
                sorted(su.difference(
                    VmW, V[V.index(T[interv[1]]):], 'name'), key=sortByName),
                domain, experiments
            ))

            removed = su.difference(
                V[V.index(T[interv[1]]) + 1:], su.union(W, experiments, 'name'), 'name')
            intervCond = V[0: V.index(T[interv[0]])]

            if not su.isEmpty(removed):
                overlineVars = su.union(
                    su.union(intervCond, removed, 'name'), experiments, 'name')
                expFactors = factors + previousFactors[i:]
                expFactors[i - 1] = eu.create('color',
                                              ['#007bff', expFactors[i - 1]])

                trace = Trace()
                trace.query = eu.create('product', expFactors)
                trace.result = None
                trace.algorithmInfo = {
                    'algName': alg_name, 'line': docalc_rule3, 'args': {
                        'indeps': [
                            eu.create('indep', [
                                sorted(removed, key=sortByName),
                                sorted(scope, key=sortByName),
                                sorted(su.union(intervCond, experiments,
                                       'name'), key=sortByName),
                                eu.create(
                                    'concat', ['G_{\\overline{', sorted(overlineVars, key=sortByName), '}}'])
                            ])
                        ]
                    }
                }
                trace.subgraph = {
                    'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                    'over': sorted(su.union(gu.nodeToList(overlineVars), expNames))
                }

                traces.append(self.pushTrace(trace))

        return {'factors': factors, 'traces': traces}

    # Node[], Node[], Node[], Node[], number[][], Expression[], number, Node[]
    # { factors: Expression[], traces: Trace[] }

    def rule2ToFactors(self, W, T, V, VmW, intervals, previousFactors, domain=0, experiments=None):
        factors = []
        traces = []
        i = 0
        expNames = list(
            map(lambda n: n['name'], experiments)) if experiments is not None else []

        for interv in intervals:
            scope = list(reversed(T[interv[0]: interv[1] + 1]))

            factors.append(self.createPExpression(
                sorted(scope, key=sortByName),
                sorted(list(reversed(T[0: interv[0]])), key=sortByName),
                sorted(su.difference(su.difference(VmW, T, 'name'),
                       V[V.index(T[interv[1]]):], 'name'), key=sortByName),
                domain, experiments
            ))

            # the variables to apply rule 2
            r2Op = list(reversed(su.difference(
                T[0: interv[0]], su.union(W, experiments, 'name'), 'name')))

            if not eu.isEmpty(r2Op):
                intervCond = V[0: V.index(T[interv[0]])]
                overlineVars = su.union(su.difference(
                    intervCond, T, 'name'), experiments, 'name')
                expFactors = factors + previousFactors[i + 1:]
                expFactors[i] = eu.create('color', ['#007bff', expFactors[i]])

                trace = Trace()
                trace.query = eu.create('product', expFactors)
                trace.result = None
                trace.algorithmInfo = {
                    'algName': alg_name, 'line': docalc_rule2, 'args': {
                        'indeps': [
                            eu.create('indep', [
                                sorted(r2Op, key=sortByName),
                                sorted(scope, key=sortByName),
                                sorted(su.union(overlineVars, su.union(su.intersection(
                                    intervCond, W, 'name'), experiments, 'name'), 'name'), key=sortByName),
                                eu.create('concat', ['G_{\\overline{', sorted(
                                    overlineVars, key=sortByName), '}\\underline{', sorted(r2Op, key=sortByName), '}}'])
                            ])
                        ]
                    }
                }
                trace.subgraph = {
                    'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                    'over': sorted(su.union(gu.nodeToList(overlineVars), expNames)),
                    'under': sorted(gu.nodeToList(r2Op))
                }

                traces.append(self.pushTrace(trace))

            i = i + 1

        return {'factors': factors, 'traces': traces}

    # Node[], Node[], Node[], number[][], number, Node[]
    # { factors: Expression[], factorSpecs: number[], traces: Trace[] }

    def breakConditionals(self, T, V, VmW, intervals, domain=0, experiments=None):
        factors = []
        factorSpecs = []
        brokenCount = 0
        expNames = list(
            map(lambda n: n['name'], experiments)) if experiments is not None else []

        for interv in intervals:
            interventions = su.difference(su.difference(
                VmW, T, 'name'), V[V.index(T[interv[0]]):], 'name')
            conditionalPart = list(reversed(T[0: interv[0]]))

            # leave the expression intact
            if su.isEmpty(interventions) or len(conditionalPart) == 0:
                factors.append(self.createPExpression(
                    sorted(
                        list(reversed(T[interv[0]: interv[1] + 1])), key=sortByName),
                    sorted(conditionalPart, key=sortByName),
                    sorted(su.difference(su.difference(VmW, T, 'name'),
                           V[V.index(T[interv[0]]):], 'name'), key=sortByName),
                    domain, experiments
                ))

                factorSpecs.append(factor_terminal if su.isEmpty(
                    interventions) else factor_subgoal)
            else:
                # break the conditional expression into numerator and denominator
                numerator = self.createPExpression(
                    sorted(
                        list(reversed(T[0: interv[1] + 1])), key=sortByName), [],
                    sorted(interventions, key=sortByName), domain, experiments
                )

                denominator = self.createPExpression(
                    sorted(conditionalPart, key=sortByName), [],
                    sorted(interventions, key=sortByName), domain, experiments
                )

                factors.append(eu.create('frac', [numerator, denominator]))
                factorSpecs.append(factor_fraction)

                brokenCount = brokenCount + 1

        traces = []

        # a trace for breaking down the conditionals
        if brokenCount > 0:
            trace = Trace()
            trace.query = eu.create('product', factors)
            trace.result = None
            trace.algorithmInfo = {'algName': alg_name,
                                   'line': docalc_cond_prob, 'args': {}}
            trace.subgraph = {
                'V': sorted(su.union(su.union(gu.nodeToList(V), self.latentNodeNames), expNames)),
                'over': sorted(expNames)
            }

            traces = [self.pushTrace(trace)]

        return {'factors': factors, 'factorSpecs': factorSpecs, 'traces': traces}

    # Node[], Node[]
    # number[][]

    def splitProbExp(self, W, T):
        # this line guarantees the elements in W follow the same relative order as they do in T
        W = su.intersection(T, W, 'name')
        i = 0
        j = 0
        ini = len(T) - 1
        intervals = []

        while i < len(W):
            while (i < len(W) and W[len(W) - 1 - i] == T[len(T) - 1 - j]):
                i = i + 1
                j = j + 1

            intervals.append([len(T) - 1 - j + 1, ini])

            while (W[len(W) - 1 - i] != T[len(T) - 1 - j]):
                j = j + 1

            ini = len(T) - 1 - j

        return intervals

    def createPExpression(self, scope, conditional=[], intervention=[], domain=0, experiments=[]):
        return self.setScripts(eu.create('prob', [
            scope,
            su.difference(conditional, experiments, 'name'),
            intervention
        ]), domain, experiments)

    def setScripts(self, P, domain, experiments):
        return TransportabilityUtils.setScripts(P, experiments, self.populations[domain] if self.populations is not None and len(self.populations) > 1 else None)

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

    # private createFailureMessage(witness: any): Failure<any> {

    #     let numDomains: number = Object.keys(self.experimentSpecs).length;

    #     if (numDomains > 0) {
    #         let V: Node[] = gu.filterBasicNodes(self.originalGraph.nodes);
    #         let domainIndex: number = 0;

    #         for (let popLabel in self.experimentSpecs) {
    #             let expCollections: Node[][] = self.experimentSpecs[popLabel];

    #             if (expCollections.length == 0) {
    #                 domainIndex++;
    #                 continue;
    #             }

    #             // prepend 'and' just before the last collection
    #             if (numDomains > 1) {
    #                 if (domainIndex == numDomains - 1) {
    #                     if (numDomains >= 3)
    #                         failureExp.push(eu.create('text', [', and ']));
    #                     else if (numDomains == 2)
    #                         failureExp.push(eu.create('text', [' and ']));
    #                 } else if (domainIndex > 0)
    #                     failureExp.push(eu.create('text', [', ']));
    #             }

    #             let distList: Expression[] = [];

    #             for (let i = 0; i < expCollections.length; i++) {
    #                 let exp: Node[] = expCollections[i];
    #                 let observed: Node[] = su.difference(V, exp, 'name');
    #                 let distExp: Expression = eu.create('prob', [
    #                     observed, None, exp, numDomains > 1 && popLabel == '*' ? '*' : None
    #                 ]);

    #                 distList.push(distExp);
    #             }

    #             if (expCollections.length >= 2) {
    #                 let allbutlast = distList.slice(0, distList.length - 1);
    #                 let last = distList[distList.length - 1];

    #                 let conjunctionExp: Expression;

    #                 if (distList.length >= 3)
    #                     conjunctionExp = eu.create('text', [', and ']);
    #                 else if (distList.length == 2)
    #                     conjunctionExp = eu.create('text', [' and ']);

    #                 let resultExpList: Expression = eu.create('concat', [eu.create('list', [allbutlast]), conjunctionExp, last]);

    #                 failureExp.push(resultExpList);
    #             } else
    #                 failureExp.push(eu.create('list', distList));

    #             if (domainIndex > 0)
    #                 failureExp.push(eu.create('text', [' from ' + popLabel]));

    #             domainIndex++;
    #         }
    #     } else
    #         failureExp.push(self.P);

    #     failureExp.push(eu.create('text', ['.']));

    #     return new Failure<any>(eu.create('concat', failureExp), witness);
    # }

    def getQueryExpression(self, X, Y, Z):
        return eu.create('prob', [Y, Z, X])

    def getAlgorithmTracers(self):
        return {
            # 'do-calc': new DoCalculusAlgorithmTracer()
            'do-calc': None
        }
