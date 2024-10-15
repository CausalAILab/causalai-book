from src.inference.engines.engine import Engine
from src.graph.classes.graph import Graph
from src.inference.classes.expression import Expression
from src.inference.classes.failure import Failure

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.expression_utils import ExpressionUtils as eu


class BaseEngine(Engine):

    #     private _currentQuery: CausalQuery;
    #     private _boundVariables: Variable[];
    #     private trace: Trace;
    #     private traceStack: Trace[];
    #     replaceVariables: Variable[];

    def __init__(self):
        self._currentQuery = None
        self._boundVariables = None
        self.trace = None
        self.traceStack = None
        self.replaceVariables = None

    @property
    def currentQuery(self):
        return self._currentQuery

    @currentQuery.setter
    def currentQuery(self, query):
        self._currentQuery = query
        self._boundVariables = su.union(
            query.x, su.union(query.y, query.z, 'name'), 'name')
        self.replaceVariables = []

    @property
    def boundVariables(self):
        return self._boundVariables

    # CausalQuery, Graph, EngineConfiguration
    # boolean

    def canCompute(self, query, graph, config=None):
        pass

    # CausalQuery, Graph
    # Expression | Failure<Any>

    def compute(self, query, graph, config=None):
        pass

    # Trace

    def getTrace(self):
        return self.trace

    # Dict[str, AlgorithmTracer]

    def getAlgorithmTracers(self):
        pass

    def print(self, exp):
        if isinstance(exp, Failure):
            print(eu.write(exp.message))
        else:
            print(eu.write(exp).replace(' ', ''))


#     nodesToVariables(node: Node): Variable;
#     nodesToVariables(nodes: Node[]): Variable[];
#     nodesToVariables(nodes: Node | Node[]): Variable | Variable[] {
#         let mapFn = (node: Node) => {
#             if (node["label"])
#                 return { name: node.name, label: node["label"] };
#             else
#                 return { name: node.name };
#         };
#         if (nodes instanceof Array) {
#             return nodes.map(mapFn);
#         } else {
#             return mapFn(nodes);
#         }
#     }

    def simplifyGraph(self, G):
        graph = Graph()
        graph.nodes = list(map(lambda n: self.simplifyNode(n), G.nodes))
        graph.edges = list(map(lambda e: self.simplifyEdge(e), G.edges))

        return graph

    def simplifyNode(self, node):
        return {'name': node['name'], 'label': node['label'], 'type_': node['type_']}

    def simplifyEdge(self, edge):
        return {'from_': edge['from_'], 'to_': edge['to_'], 'type_': edge['type_']}

    # CausalQuery, Graph
    # Variable[][]

    def normalizeQuery(self, query, graph):
        nodeNames = [
            list(map(lambda n: n['name'], query.y)),
            list(map(lambda n: n['name'], query.z)),
            list(map(lambda n: n['name'], query.x))
        ]

        normalized = [
            gu.getNodesByName(nodeNames[0], graph),
            gu.getNodesByName(nodeNames[1], graph),
            gu.getNodesByName(nodeNames[2], graph)
        ]

        if len(query.interventions) > 0:
            normalized.append(query.interventions)

        return normalized

    def distinguishVariables(self, expression, boundVars=[], replaceVars={}):
        if expression is None:
            return

        if not boundVars or len(boundVars) == 0:
            boundVars = self.boundVariables

        # replace label
        if not isinstance(expression, Expression):
            if isinstance(expression, list):
                for i in range(len(expression)):
                    exp = expression[i]

                    if not isinstance(exp, Expression) and 'name' in exp and exp['name'] is not None and exp['name'] in replaceVars:
                        expression[i] = replaceVars[exp['name']]

            elif 'name' in expression and expression['name'] is not None and expression['name'] in replaceVars:
                expression['label'] = replaceVars[expression['name']]

        else:
            if expression.type_ == 'sum':
                # if the sumover variables include bound variables,
                # replace the label of that variable
                # make recursive calls on 1) variables to sum over, and 2) the main expression
                inter = su.intersection(expression.parts[0], boundVars, 'name')
                nReplaceVars = ou.clone(replaceVars)

                if not su.isEmpty(inter):
                    for v in inter:
                        nVariable = {
                            'name': v['name'],
                            'label': (v['label'] if v['label'] is not None else v['name']) + "'"
                        }

                        if v['label'] == v['name'] + "'":
                            nReplaceVars[v['name']] = v
                        else:
                            nReplaceVars[v['name']] = nVariable

                self.distinguishVariables(
                    expression.parts[0], boundVars, nReplaceVars)
                self.distinguishVariables(
                    expression.parts[2], boundVars, nReplaceVars)
            else:
                for part in expression.parts:
                    self.distinguishVariables(part, boundVars, replaceVars)

        return replaceVars

    def distinguishVariablesTrace(self, trace, replaceVars={}):
        repVars = self.distinguishVariables(
            trace.query, self.boundVariables, replaceVars)
        self.distinguishVariablesTraceArgs(trace, replaceVars)

        if trace.children is not None:
            for child in trace.children:
                self.distinguishVariablesTrace(child, repVars)
                self.distinguishVariablesTraceArgs(trace, repVars)

    def distinguishVariablesTraceArgs(self, trace, replaceVars={}):
        if trace.algorithmInfo and 'args' in trace.algorithmInfo:
            if 'S' in trace.algorithmInfo['args']:
                self.distinguishVariables(
                    trace.algorithmInfo['args']['S'], self.boundVariables, replaceVars)

            if 'indep' in trace.algorithmInfo['args']:
                self.distinguishVariables(
                    trace.algorithmInfo['args']['indep'], self.boundVariables, replaceVars)

            if 'indeps' in trace.algorithmInfo['args']:
                self.distinguishVariables(
                    trace.algorithmInfo['args']['indeps'][0], self.boundVariables, replaceVars)

    def clearTrace(self):
        self.traceStack = []
        self.trace = None

    # Trace
    # Trace

    def pushTrace(self, trace):
        if self.traceStack is None or trace is None:
            return None

        self.traceStack.append(trace)

        if self.trace is None:
            self.trace = trace
        else:
            if self.trace.children is not None:
                self.trace.children.append(trace)
            else:
                self.trace.children = [trace]

            self.trace = trace

        return trace

    # Trace

    def popTrace(self):
        if self.traceStack is None or len(self.traceStack) == 0:
            return None

        trace = self.traceStack.pop()

        if len(self.traceStack) > 0:
            self.trace = self.traceStack[len(self.traceStack) - 1]
        else:
            self.trace = None

        return trace

    # Trace, number

    def numberTrace(self, rootTrace, start=1):
        fringe = [rootTrace]
        inc = start

        while len(fringe) > 0:
            trace = fringe.pop()

            if trace.children is not None:
                for i in range(len(trace.children) - 1, 0, -1):
                    fringe.append(trace.children[i])

            trace.number = inc
            inc = inc + 1
