import functools

from src.graph.classes.graph_defs import latentNodeType
from src.inference.engines.base_engine import BaseEngine
from src.transportability.classes.transportability import targetPopulation
from src.selection_bias.classes.selection_bias import selectionBiasNodeType
from src.inference.classes.trace import Trace
from src.inference.classes.failure import Failure
from src.inference.classes.expression import Expression
from src.path_analysis.d_separation import DSeparation
from src.inference.utils.graph_utils import sortByName, compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.projection.projection_utils import ProjectionUtils
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.compute.compute_utils import ComputeUtils as cu
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.confounding_analysis import ConfoundingAnalysis

from src.error.error_messages import defaultErrorMessage

alg_name = 'SB'

sb_base = 0
sb_rule1 = 1
sb_rule2 = 2
sb_rule3 = 3


class SelectionBiasEngine(BaseEngine):

    # private originalGraph: Graph;
    # private orderedV: Node[];
    # private T: Node[];
    # private T0: Node[];
    # private Tprime: Node[];
    # private P: Expression;

    def __init__(self):
        super().__init__()

        self.originalGraph = None
        self.orderedV = None
        self.T = None
        self.T0 = None
        self.Tprime = None
        self.P = None

    # CausalQuery, Graph, EngineConfiguration
    # boolean
    def canCompute(self, query, G, config=None):
        if not query or not G:
            return False

        nonBasicNodes = su.difference(
            G.nodes, gu.filterBasicNodes(G.nodes, False), 'name')
        unsupportedNodes = list(
            filter(lambda n: n['type_'] != selectionBiasNodeType.id_, nonBasicNodes))

        if len(unsupportedNodes) > 0:
            return False

        if not cu.inSBContext(G):
            return False

        populations = config['populations'] if config is not None and 'populations' in config else [
            targetPopulation]

        if len(populations) > 1:
            return False

        return True

    # CausalQuery, Graph, EngineConfiguration
    # Expression | Failure<Any>

    def compute(self, query, G, config=None):
        S = cu.getSelectionBiasNode(G)

        if S is None:
            return self.createErrorMessage()

        self.clearTrace()

        graph = ProjectionUtils.projectOverNonLatentNodes(G)

        self.originalGraph = graph
        self.currentQuery = query

        [y, z, x] = self.normalizeQuery(query, graph)

        V = gu.filterBasicNodes(graph.nodes)
        V = sorted(V, key=sortByName)

        self.T0 = config['externalData'] if config is not None and 'externalData' in config else []
        self.T0 = list(map(lambda n: self.simplifyNode(n), self.T0))

        self.P = eu.create(
            'prob', [gu.nodesToVariables(V), [eu.create('=', [S, '1'])]])

        isConditional = z is not None and not su.isEmpty(z)

        try:
            result = None
            simplified = False

            if isConditional:
                result = self.trySimpleDerivation(y, x, z, self.P, graph)
                simplified = result is not None

                if not simplified:
                    return self.createUnsupportedMessage()

            if not simplified:
                # remove the original trace since derviation steps is not supported
                self.popTrace()
                result = self.recoverc(
                    y, x, z, self.P, graph) if isConditional else self.recover(y, x, self.P, graph)

            result = pu.simplify(result)

            if config is not None and 'renameReinstantiatedVariables' in config and config['renameReinstantiatedVariables'] == True:
                self.distinguishVariables(result, self.replaceVariables)

            return result
        except Exception as error:
            if self.getTrace() is not None:
                self.getTrace().result = error

            return error

    # Node[], Node[], Node[], Expression, Graph
    # Expression

    def recoverc(self, y, x, z, P, G):
        query = eu.create('prob', [y, z, x])
        trace = Trace()
        trace.query = query
        trace.result = None
        trace.data = P
        trace.subgraph = gu.nodeToList(G.nodes)

        self.pushTrace(trace)

        return self._recoverc(y, x, z, P, G)

    # Node[], Node[], Expression, Graph
    # Expression

    def recover(self, y, x, P, G):
        return self.idsb(y, x, P, G)

    # Node[], Node[], Node[], Expression, Graph
    # Expression

    def _recoverc(self, y, x, z, P, G):
        for varZ in z:
            zMVarZ = su.difference(z, [varZ])

            if DSeparation.test(gu.transform(G, x, [varZ]), y, [varZ], su.union(x, zMVarZ)):
                return self._recoverc(y, su.union(x, [varZ]), zMVarZ, P, G)

        Pp = self.recover(su.union(y, z), x, P, G)

        return eu.create('frac', [Pp, pu.sumOver(ou.clone(Pp), y)])

    # Node[], Node[], Expression, Graph
    # Expression

    def idsb(self, y, x, P, G):
        S = cu.getSelectionBiasNode(G)

        if S is None:
            return None

        V = gu.filterBasicNodes(G.nodes)
        self.orderedV = su.difference(gu.topoSort(G, True), [S], 'name')
        AnY = gu.ancestors(y, G)
        AnS = gu.ancestors(S, G)
        W = su.union(AnY, AnS, 'name')
        G_W = gu.subgraph(G, W)
        PW = pu.sumOver(P, su.difference(V, W, 'name'))
        TAndW = su.intersection(self.T0, W, 'name')
        self.Tprime = []

        for w in W:
            if su.equals([w], [S], 'name') or su.belongs(w, TAndW, compareNames):
                continue

            if DSeparation.test(G_W, S, w, TAndW):
                self.Tprime.append(w)

        self.T = su.union(self.Tprime, TAndW, 'name')
        T = self.T
        D = gu.ancestors(y, gu.subgraph(G_W, su.difference(W, x, 'name')))
        R = su.difference(W, T, 'name')
        A = su.intersection(su.difference(D, y, 'name'), T, 'name')
        B = su.intersection(su.difference(D, y, 'name'), R, 'name')

        G_D = gu.subgraph(G_W, D)
        PJ_GT = ProjectionUtils.projectOver(G_W, T)
        PJ_GDDB = ProjectionUtils.projectOver(G_D, su.difference(D, B, 'name'))

        C_G_D = gu.cCompDecomposition(G_D)
        C_PJ_GT = gu.cCompDecomposition(PJ_GT)
        C_PJ_GDDB = gu.cCompDecomposition(PJ_GDDB)

        factors = []

        # step 5
        for Ci in C_PJ_GDDB:
            # parents in which graph?
            PaCi = su.union(Ci, gu.parents(Ci, self.originalGraph), 'name')
            lhs = su.intersection(B, PaCi, 'name')
            rhs = su.intersection(R, PaCi, 'name')
            equal = su.equals(lhs, rhs, 'name')

            QBCi = None

            if equal:
                Tk = None

                for Ti in C_PJ_GT:
                    if su.isSubset(Ci, Ti, 'name'):
                        Tk = Ti
                        break

                if Tk is None:
                    raise self.createErrorMessage()

                Torder = su.intersection(self.orderedV, T, 'name')

                PT = None

                if len(self.T0) > 0:
                    PT = eu.create('product', [
                        eu.create('prob', [self.Tprime, su.union(
                            self.T0, [eu.create('=', [S, '1'])])]),
                        eu.create('prob', [self.T0])
                    ])
                else:
                    PT = eu.create('prob', [self.Tprime, su.union(
                        self.T0, [eu.create('=', [S, '1'])])])

                PJ_Tk = gu.subgraph(PJ_GT, Tk)

                QBCi = self.qIdentify(
                    Ci, Tk, ConfoundingAnalysis.qComputeCComp(Tk, Torder, PT), PJ_Tk)

            if not equal or not isinstance(QBCi, Expression):
                Fi = []
                Bi = []
                CiF = gu.reach(Ci, gu.transform(
                    G_D, None, su.intersection(G_D.nodes, PJ_GDDB.nodes)))

                for Dj in C_G_D:
                    if len(su.intersection(CiF, Dj, 'name')) > 0:
                        Fi.append(Dj)

                if not Fi or len(Fi) == 0:
                    raise self.createErrorMessage()

                for fi in Fi:
                    Bi = Bi + su.difference(fi, Ci, 'name')

                QDiExps = []

                for Di in Fi:
                    QDiExps.append(self.rce(Di, PW, G_W))

                rceExp = eu.create('product', QDiExps)
                QBCi = pu.sumOver(rceExp, Bi)

            factors.append(QBCi)

        # sort by reverse topological order, and 'push in' the sum
        factors.reverse()

        def sortBySummation(f1, f2):
            if f1.type_ == 'sum' and f2.type_ != 'sum':
                return 1
            elif f1.type_ != 'sum' and f2.type_ == 'sum':
                return -1
            else:
                return 0

        factors = sorted(factors, key=functools.cmp_to_key(sortBySummation))

        return pu.sumOver(eu.create('product', factors), A)

    # Node[], Expression, Graph
    # Expression

    def rce(self, E, P, G):
        S = cu.getSelectionBiasNode(G)
        V = gu.filterBasicNodes(G.nodes)
        AnE = gu.ancestors(E, G)
        AnS = gu.ancestors(S, G)
        W = su.union(AnE, AnS, 'name')
        VMinusW = su.difference(V, W, 'name')

        # step 1
        if not su.isEmpty(VMinusW):
            return self.rce(E, pu.sumOver(P, VMinusW), gu.subgraph(G, W))

        # step 2
        CG = gu.cCompDecomposition(G)
        recoverableCG = self.getRecoverableCComponents(G.nodes, self.T, G)
        C = []
        Ci = None

        for comp in recoverableCG:
            C = su.union(C, comp, 'name')

            if su.isSubset(E, comp, 'name'):
                Ci = comp

        # step 3
        if not su.isEmpty(C):
            # 3.a
            if Ci is not None:
                G_Ci = gu.subgraph(G, Ci)

                return self.qIdentify(E, Ci, self.qRecover(Ci, G.nodes, self.T, P, G), G_Ci)

            # 3.b
            ProdQCi = []

            for Cii in recoverableCG:
                ProdQCi.append(self.qRecover(Cii, G.nodes, self.T, P, G))

            PDivideProdQCi = eu.create('frac', [
                P,
                eu.create('product', ProdQCi)
            ])

            VS = su.union(V, [S], 'name')
            G_VSMinusC = gu.subgraph(G, su.difference(VS, C, 'name'))

            return self.rce(E, PDivideProdQCi, G_VSMinusC)

        # step 4
        for Bi in CG:
            if su.isSubset(E, Bi, 'name'):
                continue

            AnBi = gu.ancestors(Bi, G)
            Z = su.difference(V, su.union(AnS, AnBi, 'name'), 'name')

            if su.isEmpty(Z):
                continue

            VS = su.union(V, [S], 'name')
            G_VSMinusZ = gu.subgraph(G, su.difference(VS, Z, 'name'))
            QBi = self.rce(Bi, pu.sumOver(P, Z), G_VSMinusZ)

            G_VSMinusBi = gu.subgraph(G, su.difference(VS, Bi, 'name'))
            PDivideQBi = eu.create('frac', [P, QBi])

            return self.rce(E, PDivideQBi, G_VSMinusBi)

        raise self.createFailureMessage(G)

    # Thm. 3
    # Returns a list of c-components recoverable from f(P(v|S=1)) with available P(t)
    # Node[], Node[], Graph
    # Node[][]

    def getRecoverableCComponents(self, H, T, G):
        S = cu.getSelectionBiasNode(G)
        V = gu.filterBasicNodes(G.nodes)
        G_H = gu.subgraph(G, H)
        C_G_H = gu.cCompDecomposition(G_H)

        T0H = su.difference(T, gu.descendants(
            su.difference(V, H, 'name'), G), 'name')
        Tprime = []

        for h in H:
            if su.equals([h], [S], 'name') or su.belongs(h, T0H, compareNames):
                continue

            if DSeparation.test(G_H, h, S, T0H):
                Tprime.append(h)

        TH = su.union(T0H, Tprime, 'name')
        RH = su.difference(su.difference(H, TH, 'name'), [S], 'name')
        Hs = None

        for Hi in C_G_H:
            if su.belongs(S, Hi, compareNames):
                Hs = Hi
                break

        if Hs is None:
            raise self.createErrorMessage()

        AnHs = gu.ancestors(Hs, G_H)
        ChRH = su.union(RH, gu.children(RH, G_H), 'name')
        recoverable = []

        for Hj in C_G_H:
            if su.isEmpty(su.intersection(Hj, su.intersection(AnHs, ChRH, 'name'), 'name')):
                recoverable.append(Hj)

        return recoverable

    # Thm. 3
    # Recovers Q[Hi] from f(P(v|S=1)) with available P(t)
    # Node[], Node[], Node[], Expression, Graph
    # Expression

    def qRecover(self, Hi, H, T, P, G):
        S = cu.getSelectionBiasNode(G)
        V = gu.filterBasicNodes(G.nodes)
        G_H = gu.subgraph(G, H)
        C_G_H = gu.cCompDecomposition(G_H)
        orderedH = su.difference(gu.topoSort(G_H, True), [S], 'name')

        T0H = su.difference(T, gu.descendants(
            su.difference(V, H, 'name'), G), 'name')
        Tprime = []

        for h in H:
            if su.equals([h], [S], 'name') or su.belongs(h, T0H, compareNames):
                continue

            if DSeparation.test(G_H, h, S, T0H):
                Tprime.append(h)

        TH = su.union(T0H, Tprime, 'name')

        # lemma 1
        # recover P(TH) from P(T0 in TH0) and P(T' in TH0)
        PTH = None

        TprimeinTH0 = su.intersection(T0H, self.Tprime, 'name')
        T0inTH0 = su.intersection(T0H, self.T0, 'name')

        if len(TprimeinTH0) == 0:
            PTH = eu.create('prob', [T0inTH0])
        else:
            PTH = eu.create('product', [
                eu.create('prob', [TprimeinTH0, eu.create(
                    'list', [T0inTH0, eu.create('=', [S, '1'])])]),
                eu.create('prob', [T0inTH0])
            ])

        Hs = None

        for Hii in C_G_H:
            if su.belongs(S, Hii, compareNames):
                Hs = Hii
                break

        if Hs is None:
            raise self.createErrorMessage()

        AnHs = gu.ancestors(Hs, G_H)
        QHi = None
        S1 = su.intersection(Hi, AnHs, 'name')
        S2 = su.difference(Hi, AnHs, 'name')
        S1Factors = []
        S2Factors = []

        for v in S1:
            i = orderedH.index(v)

            PvhTH = None

            if su.equals(TH, T0H, 'name'):
                PvhTH = PTH
            else:
                HSTH = su.difference(su.difference(H, [S], 'name'), TH, 'name')
                HST0H = su.difference(su.difference(
                    H, [S], 'name'), T0H, 'name')

                PvhTH = eu.create('product', [
                    eu.create('frac', [
                        pu.sumOver(P, HSTH),
                        pu.sumOver(P, HST0H)
                    ]),
                    PTH
                ])

            HAfteri = orderedH[i + 1:]
            HWithi = orderedH[i:]
            sumOverTop = su.intersection(HAfteri, TH, 'name')
            sumOverBottom = su.intersection(HWithi, TH, 'name')

            topExp = pu.sumOver(PvhTH, sumOverTop)
            bottomExp = pu.sumOver(PvhTH, sumOverBottom)
            exp = eu.create('frac', [topExp, bottomExp])

            S1Factors.append(exp)

        for v in S2:
            i = orderedH.index(v)
            HAfteri = orderedH[i + 1:]

            topExp = pu.sumOver(P, HAfteri)
            bottomExp = pu.sumOver(P, su.union(HAfteri, [v], 'name'))
            exp = eu.create('frac', [topExp, bottomExp])

            S2Factors.append(exp)

        QHi = eu.create('product', S1Factors + S2Factors)

        return QHi

    # Node[], Node[], Expression, Graph
    # Expression

    def qIdentify(self, C, T, Q, G):
        A = su.intersection(gu.ancestors(C, gu.subgraph(G, T)), T, 'name')

        if su.equals(A, C):
            return pu.sumOver(Q, su.difference(T, C, 'name'))
        elif su.equals(A, T):
            raise self.createFailureMessage(G)
        else:
            QA = pu.sumOver(Q, su.difference(T, A, 'name'))
            G_A = gu.subgraph(G, A)
            CG_A = gu.cCompDecomposition(G_A)

            for Tip in CG_A:
                if su.isSubset(C, Tip, 'name'):
                    Ti = su.intersection(Tip, A, 'name')
                    QTi = ConfoundingAnalysis.qComputeCComp(
                        Ti, su.intersection(self.orderedV, A, 'name'), QA)
                    G_Ti = gu.subgraph(G, Ti)

                    # should it be the same graph or the subgraph?
                    return self.qIdentify(C, Ti, QTi, G_Ti)

    def trySimpleDerivation(self, y, x, z, P, G):
        S = cu.getSelectionBiasNode(G)

        if not DSeparation.test(gu.transform(G, x, None), S, y, su.union(x, z, 'name')):
            return None

        if not DSeparation.test(gu.transform(G, None, x), y, x, z):
            return None

        queryExpression = eu.create('prob', [y, z, x])
        resultExp = eu.create('prob', [y, eu.create(
            'list', [su.union(x, z, 'name'), eu.create('=', [S, '1'])])])

        # rule 2: x \indep y | z in G_x_bar, P(y|x,z)
        # rule 1: S \indep y | x,z, P(y|x,z,S=1)

        indepTrace = Trace()
        indepTrace.query = resultExp
        indepTrace.result = None
        indepTrace.algorithmInfo = {
            'algName': alg_name, 'line': sb_rule1, 'args': {
                'indeps': [
                    eu.create('indep', [S, y, su.union(x, z, 'name')])
                ]
            }
        }
        indepTrace.subgraph = {'V': gu.nodeToList(G.nodes)}

        rule2Trace = Trace()
        rule2Trace.query = eu.create('prob', [y, su.union(x, z, 'name')])
        rule2Trace.result = None
        rule2Trace.algorithmInfo = {
            'algName': alg_name, 'line': sb_rule2, 'args': {
                'indeps': [
                    eu.create('indep', [x, y, z, eu.create(
                        'concat', ['G_{\\underline{', x, '}}'])])
                ]
            }
        }
        rule2Trace.subgraph = {'V': gu.nodeToList(
            G.nodes), 'under': gu.nodeToList(x)}
        rule2Trace.children = [indepTrace]

        rootTrace = Trace()
        rootTrace.query = queryExpression
        rootTrace.result = resultExp
        rootTrace.algorithmInfo = {
            'algName': alg_name, 'line': sb_base, 'args': {}}
        rootTrace.children = [rule2Trace]

        self.pushTrace(rootTrace)
        self.numberTrace(rootTrace)

        return resultExp

    def createFailureMessage(self, witness):
        expression = eu.create('concat', [
            eu.create('text', ['The recoverability of ']),
            eu.create('prob', [self.currentQuery.y,
                      self.currentQuery.z, self.currentQuery.x]),
            eu.create('text', [' cannot be determined.'])
        ])

        return Failure(expression, witness)

    def createUnsupportedMessage(self):
        expression = eu.create('concat', [
            eu.create('text', ['The recoverability of ']),
            eu.create('prob', [self.currentQuery.y,
                      self.currentQuery.z, self.currentQuery.x]),
            eu.create('text', [' cannot be determined.'])
        ])

        return Failure(expression, None)

    def createErrorMessage(self):
        return Failure(eu.create('text', [defaultErrorMessage]), None)

    # Dict[str, AlgorithmTracer]

    def getAlgorithmTracers(self):
        return {
            # 'SB': SelectionBiasAlgorithmTracer()
            'SB': None
        }
