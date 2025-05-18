from inference.engines.base_engine import BaseEngine
 
class LinearEngine(BaseEngine):
 
    # query: CausalQuery, graph: Graph, config: EngineConfiguration
    # returns bool
    def canCompute(self, query, graph, config = None):
        pass

    # returns Expression | Failure<Any>
    def compute(self, query, graph, config = None):
        pass

    # returns Trace
    def getTrace(self):
        pass

    # returns Dict[str, AlgorithmTracer]
    def getAlgorithmTracers(self):
        pass