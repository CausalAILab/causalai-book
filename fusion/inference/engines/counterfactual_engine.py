import functools

from src.graph.classes.graph_defs import latentNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation
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


alg_name = 'cf-id'

op_sum_anc = 1
op_c_decomp = 2
op_transp = 3

cf_base = 0
cf_sum_over = 1
# cf_composition_add_ancestors = 2
# cf_exclusion_restrictions = 3
# cf_independence_restrictions = 4
cf_independence = 5
cf_cond_prob = 6
cf_chain_rule = 7
cf_comp_factor = 8
cf_comp_num = 9
cf_comp_den = 10
cf_remove_counterfactuals = 11
cf_c_component_form = 12
cf_c_component = 13
cf_same_domain_exp = 14

factor_fraction = 0
factor_terminal = 1
factor_subgoal = 2




def cf_node(node, had = []):
    nodes = ou.makeArray(node)

    def node_cf(n):
        return {'name': n['name'], 'label': n['label']}

    exps = list(map(node_cf, nodes))

    if isinstance(node, list):
        return exps
    else:
        return exps[0]


def cf_exp(node, had = []):
    nodes = ou.makeArray(node)

    def exp_cf(n):
        return eu.create('countfact', [n, had])

    exps = list(map(exp_cf, nodes))

    if isinstance(node, list):
        return exps
    else:
        return exps[0]


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
        self.latentNodes = []
        self.latentNodeNames = []
        self.originalGraph = None
        self.populations = []
        self.experiments = None
 

    # CausalQuery, Graph, EngineConfiguration
    # boolean
    def canCompute(self, query, G, config = None):
        if not query or not G:
            return False

        if not su.isEmpty(query.z):
            return False

        unsupportedNodes = su.difference(G.nodes, gu.filterBasicNodes(G.nodes, False), 'name')

        if len(unsupportedNodes) > 0:
            return False

        return True


    # Expression | Failure<Any>
    def compute(self, query, G, config = None):
        self.populations = [targetPopulation]
        self.experiments = config['experiments'] if config is not None and 'experiments' in config else []

        self.clearTrace()

        graph = ProjectionUtils.projectOverNonLatentNodes(G)
        
        self.originalGraph = graph = self.simplifyGraph(graph)
        self.latentNodes = list(filter(lambda n: n['type_'] == latentNodeType.id_, graph.nodes))
        self.latentNodeNames = list(map(lambda n: n['name'], self.latentNodes))
        
        self.currentQuery = query

        [y, z, x] = self.normalizeQuery(query, graph)

        V = sorted(graph.nodes, key = sortByName)

        self.P = self.setScripts(eu.create('prob', [gu.nodesToVariables(V)]), 0, None)

        try:
            trace = Trace()
            trace.query = eu.create('=', [self.createPExpression(y, z, x, 0, None), self.createPExpression(cf_exp(y, x), cf_exp(z, x), [], 0, None)])
            trace.result = None
            trace.subgraph = su.union(gu.nodeToList(graph.nodes), self.latentNodeNames)
            trace.algorithmInfo = { 'algName': alg_name, 'line': cf_base, 'args': {} }
            
            trace = self.pushTrace(trace)

            result = self.identify(y, x, self.P, graph)
            result = pu.simplify(result)

            if config is not None and 'renameReinstantiatedVariables' in config and config['renameReinstantiatedVariables'] == True:
                self.distinguishVariables(result, self.replaceVariables)

            trace.result = result

            self.numberTrace(trace)

            return result
        except Exception as error:
            if self.getTrace() is not None:
                self.getTrace().result = error
                
            return error


    # Node[], Node[], Expression, Graph
    # Expression
    def identify(self, y, x, P, G):
        V = gu.topoSort(G, True)
        V = gu.filterBasicNodes(V)

        Xp = su.difference(V, x, 'name')
        D = su.intersection(V, gu.ancestors(y, gu.subgraph(G, Xp)), 'name')
        G_D = gu.subgraph(G, D)
        CG_D = gu.cCompDecomposition(G_D, True)
        nCG_D = len(CG_D)
        DmY = su.difference(D, y, 'name')
        queryFactors = []
        factors = []
        
        Pv = self.createPExpression(list(reversed(cf_node(D, x))), [], [], 0, None)

        # trace that specifies the required sum
        if not su.isEmpty(DmY):
            trace = Trace()
            trace.query = eu.create('sum', [DmY, None, Pv])
            trace.result = None
            trace.subgraph = gu.nodeToList(G.nodes)
            trace.algorithmInfo = { 'algName': alg_name, 'line': cf_sum_over, 'args': { 'S': DmY } }
            
            trace = self.pushTrace(trace)

        V_pa = list(map(lambda vi: cf_node(vi, gu.parents(vi, G)), V))
        D_pa = su.intersection(V_pa, D, 'name')

        # c-component decomposition trace
        if nCG_D > 1:
            trace = Trace()
            trace.query = None
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': cf_c_component_form,
                'args': { 'numCComps': nCG_D, 'cComponents': CG_D, 'factors': queryFactors, 'Pv': Pv }
            }
            
            trace = self.pushTrace(trace)

        # go over each c-component in reverse order
        for Di in CG_D:
            Di_pa = su.intersection(D_pa, Di, 'name')

            queryFactors.append(self.createPExpression(Di_pa, [], [], 0, None))

            # if there is more than one c-component create a trace for a new branch in the tree
            if nCG_D > 1:
                trace = Trace()
                trace.query = queryFactors[len(queryFactors) - 1]
                trace.result = None
                trace.algorithmInfo = { 'algName': alg_name, 'line': cf_c_component, 'args': {} }
                trace.subgraph = gu.nodeToList(V)
                
                trace = self.pushTrace(trace)

            fExp = self.qIdentify(Di_pa, V_pa, G)

            # if there is more than one c-component we need to pop the previously created trace
            if nCG_D > 1:
                self.popTrace().result = fExp

            factors.append(fExp)

        # if there was more than one c-component, pop that trace
        if nCG_D > 1:
            self.popTrace().query = eu.create('sum', [DmY, None, eu.create('product', queryFactors)])

        # if there was a sum, pop that trace
        if not su.isEmpty(DmY):
            self.popTrace()

        # sort c-factors with summations at the end
        def sortBySummation(f1, f2):
            if f1.type_ == 'sum' and f2.type_ != 'sum':
                return 1
            elif f1.type_ != 'sum' and f2.type_ == 'sum':
                return -1
            else:
                return 0
        
        factors = sorted(factors, key = functools.cmp_to_key(sortBySummation))

        return pu.sumOver(eu.create('product', factors), DmY)


    # /**
    #  * Identifies the distribution Q[C] from P(v)=Q[V] in the graph G
    #  * @param C A set of variables such that C \subset T and G_C has a single c-component. 
    #  * The very same objects in C have to be in array V
    #  * @param V The set of observable variables
    #  * @param G A graph over the variables in V
    #  * @returns An expression for Q[C] in terms of P(v)
    #  */
    def qIdentify(self, C, V, G):
        steps = list(reversed(self.derive(C, V, G)))
        return self.unroll(C, V, steps, G)


    # /**
    #  * Derives a expression for P_{v \ c}(c) in terms of P_{v \ t}(t)
    #  * @param C A set of variables such that C \subset T and G_C has a single c-component
    #  * @param T A set of variables
    #  * @param G A graph over the variables in T
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
    def unroll(self, W, V, rSteps, G, domain = 0, experiments = None):
        step = None
        
        if len(rSteps) > 0:
            step = rSteps.pop()
        
        VmW = su.difference(V, W, 'name')
        VmWmExp = su.difference(VmW, experiments, 'name')
        
        if step is None and su.isEmpty(VmWmExp):
            return self.removeCounterfactuals(V, [], domain, experiments)
        elif step is None:
            raise self.createFailureMessage(G)
        
        if step['op'] == op_sum_anc:
            return self.unrollSumAnc(step, W, V, rSteps, G, domain, experiments)
        elif step['op'] == op_c_decomp:
            return self.unrollCDecomp(step, W, V, VmW, rSteps, G, domain, experiments)
        elif step['op'] == op_transp:
            return self.unrollTransp(step, W, V, VmW, rSteps, G, domain, experiments)
        else:
            raise self.createFailureMessage('Unknown derivation operation: ' + step['op'])


    # DerivationStep, Node[], Node[], DerivationStep[], Graph, number, Node[]   
    # Expression
    def unrollSumAnc(self, step, W, V, rSteps, G, domain = 0, experiments = None):
        T = su.intersection(V, step['T'], 'name')
        # variables to sum over
        TmW = su.difference(step['T'], W, 'name')

        final = su.isEmpty(su.difference(gu.ancestors(W, G), W, 'name'))

        if not final:
            trace = Trace()
            trace.query = pu.sumOver(self.createPExpression(list(reversed(T)), [], [], domain, experiments), TmW)
            trace.result = None
            trace.algorithmInfo = {
                'algName': alg_name, 'line': cf_sum_over, 'args': {
                    'S': TmW
                }
            }

            self.pushTrace(trace)

        exp = self.unroll(T, V, rSteps, G, domain, experiments)
        sumExp = pu.sumOver(exp, TmW)

        if not final:
            self.popTrace().result = sumExp

        return sumExp


    # DerivationStep, Node[], Node[], Node[], DerivationStep[], Graph, number, Node[]
    # Expression
    def unrollCDecomp(self, step, W, V, VmW, rSteps, G, domain = 0, experiments = None):
        T = su.intersection(V, step['T'], 'name')
        intervals = self.splitProbExp(W, T)
        traces = []
        lastFactors = [self.createPExpression(sorted(W, key = sortByName), [], [], domain, experiments)]

        # factorization
        traces = traces + self.factorize(W, T, V, VmW, intervals, domain, experiments)

        if len(traces) > 0:
            lastFactors = traces[len(traces) - 1].query.parts

        # apply independencies
        indResult = self.independenciesToFactors(W, T, V, VmW, intervals, lastFactors, domain, experiments)
        traces = traces + indResult['traces']

        # break conditional effects
        breakCondResult = self.breakConditionals(T, V, VmW, intervals, domain, experiments)
        traces = traces + breakCondResult['traces']

        if indResult['factors'] is not None:
            lastFactors = indResult['factors']

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
                    trace.algorithmInfo = { 'algName': alg_name, 'line': cf_comp_factor, 'args': {} }

                    self.pushTrace(trace)

                # a trace for solving the numerator
                if breakCondResult['factorSpecs'][i] == factor_fraction:
                    trace = Trace()
                    trace.query = breakCondResult['factors'][i].parts[0]
                    trace.result = None
                    trace.algorithmInfo = { 'algName': alg_name, 'line': cf_comp_num, 'args': {} }

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
                    trace.algorithmInfo = { 'algName': alg_name, 'line': cf_comp_den, 'args': { 'result': denResult } }

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
                    eu.create('sum', [T[interv[0]: interv[1] + 1], None, ou.clone(expEff)])
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
    def unrollTransp(self, step, W, V, VmW, rSteps, G, domain = 0, experiments = None):
        trInfoSet = step['transportabilityInfo']
        # avoids transporting from the same domain with same experiments
        trInfoSet = su.unique(trInfoSet)
        weightedResults = []
        result = None
        j = 1

        displayTrace = len(self.populations) > 1 or (len(self.populations) == 1 and len(trInfoSet) > 1)

        numTransportable = 0

        for info in trInfoSet:
            if info['domain'] != domain:
                if domain == 0:
                    numTransportable = numTransportable + 1
            else:
                numTransportable = numTransportable + 1

        for info in trInfoSet:
            dLabel = self.populations[info['domain']].label if info['domain'] is not None else ''
            expNames = list(map(lambda n: n['name'], info['experiments'])) if info['experiments'] is not None else []

            if displayTrace:
                trace = Trace()
                trace.query = self.createPExpression(sorted(W, key = sortByName), [], sorted(VmW, key = sortByName), info['domain'], info['experiments'])
                trace.result = None
                trace.algorithmInfo = {
                    'algName': alg_name, 'line': cf_same_domain_exp, 'args': {
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

            transportable = (info['domain'] != domain and domain == 0) or (info['domain'] == domain)

            if transportable:
                exp = self.unroll(W, su.difference(V, info['experiments'], 'name'), info['steps'], gu.subgraph(G, su.difference(G.nodes, info['experiments'], 'name')), info['domain'], info['experiments'])

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
                    weightedResult = eu.create('product', [eu.create('script', ['w', '' + str(j), '(' + dLabel + ')']), exp])
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
    def factorize(self, W, T, V, VmW, intervals, domain = 0, experiments = None):
        if len(intervals) <= 1:
            return []

        factors = []

        for interv in intervals:
            factors.append(self.createPExpression(
                sorted(list(reversed(T[interv[0]: interv[1] + 1])), key = sortByName),
                sorted(list(reversed(su.intersection(T[0: interv[0]], W, 'name'))), key = sortByName),
                [], domain, experiments
            ))

        # a trace for chain rule
        trace = Trace()
        trace.query = eu.create('product', factors)
        trace.result = None
        trace.algorithmInfo = { 'algName': alg_name, 'line': cf_chain_rule, 'args': {} }

        return [self.pushTrace(trace)]


    # Node[], Node[], Node[], Node[], number[][], Expression[], number, Node[]
    # { factors: Expression[], traces: Trace[] }
    def independenciesToFactors(self, W, T, V, VmW, intervals, previousFactors, domain = 0, experiments = None):
        factors = []
        traces = []
        i = 0

        for interv in intervals:
            scope = list(reversed(T[interv[0]: interv[1] + 1]))
            factors.append(self.createPExpression(
                scope,
                list(reversed(T[0: interv[0]])),
                [],
                domain, experiments
            ))

            indOp = list(reversed(su.difference(T[0: interv[0]], su.union(W, experiments, 'name'), 'name')))

            if not eu.isEmpty(indOp):
                expFactors = factors + previousFactors[i+1:]
                expFactors[i] = eu.create('color', ['#007bff', expFactors[i]])

                trace = Trace()
                trace.query = eu.create('product', expFactors)
                trace.result = None
                trace.algorithmInfo = {
                    'algName': alg_name, 'line': cf_independence, 'args': {
                        'indeps': [
                            eu.create('indep', [
                                indOp, scope,
                                W[0: W.index(T[interv[0]])]
                            ])
                        ]
                    }
                }

                traces.append(self.pushTrace(trace))

            i = i + 1

        return { 'factors': factors, 'traces': traces }


    # Node[], Node[], Node[], number[][], number, Node[]
    # { factors: Expression[], factorSpecs: number[], traces: Trace[] }
    def breakConditionals(self, T, V, VmW, intervals, domain = 0, experiments = None):
        factors = []
        factorSpecs = []
        expEff = None
        brokenCount = 0
        removedCf = []

        for interv in intervals:
            interventions = su.difference(su.difference(VmW, T, 'name'), V[V.index(T[interv[0]]):], 'name')
            conditionalPart = list(reversed(T[0: interv[0]]))

            # leave the expression intact
            if su.isEmpty(interventions) or len(conditionalPart) == 0:
                factors.append(self.removeCounterfactuals(T[interv[0]: interv[1] + 1], conditionalPart, domain, experiments))
                factorSpecs.append(factor_terminal if su.isEmpty(interventions) else factor_subgoal)
                removedCf = su.union(removedCf, T[0: interv[1] + 1], 'name')
            else:
                # break the conditional expression into numerator and denominator
                expEff = self.createPExpression(list(reversed(T[0: interv[1] + 1])), [], [], domain, experiments)

                factors.append(eu.create('frac', [
                    expEff,
                    self.createPExpression(conditionalPart, [], [], domain, experiments)
                ]))

                factorSpecs.append(factor_fraction)

                brokenCount = brokenCount + 1

        traces = []

        # a trace for breaking down the conditionals
        if brokenCount > 0:
            trace = Trace()
            trace.query = eu.create('product', factors)
            trace.result = None
            trace.algorithmInfo = { 'algName': alg_name, 'line': cf_cond_prob, 'args': {} }

            traces = [self.pushTrace(trace)]
        elif not su.isEmpty(removedCf):
            trace = Trace()
            trace.query = None
            trace.result = eu.create('product', factors)
            trace.algorithmInfo = { 'algName': alg_name, 'line': cf_remove_counterfactuals, 'args': { 'scope': T } }

            traces = [self.pushTrace(trace)]

        return { 'factors': factors, 'factorSpecs': factorSpecs, 'traces': traces }


    # Node[], Node[], number, Node[]
    # Expression
    def removeCounterfactuals(self, scope, given, domain = 0, experiments = None):
        scopeWcf = list(map(lambda n: {'name': n['name'], 'label': n['label']}, scope))
        givenWcf = list(map(lambda n: {'name': n['name'], 'label': n['label']}, given))

        exp = self.createPExpression(list(reversed(scopeWcf)), list(reversed(givenWcf)), [], domain, experiments)

        return exp


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


    def createPExpression(self, scope, conditional = [], intervention = [], domain = 0, experiments = []):
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