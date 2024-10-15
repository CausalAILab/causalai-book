

class Trace():

    # query: Expression;
    # result: Expression | Failure<any>;
    # data?: Expression;
    # simplification?: Expression;
    # /**
    #  * Names or IDs of the nodes that compose the subgraph
    #  */
    # subgraph?: string[] | TraceSubgraph;
    # children?: Trace[];
    # parent?: Trace;
    # algorithmInfo?: AlgorithmInfo;
    # number?: number;

    def __init__(self):
        self.query = None
        self.result = None
        self.data = None
        self.simplification = None
        self.subgraph = None
        self.children = None
        self.parent = None
        self.algorithmInfo = None
        self.number = None