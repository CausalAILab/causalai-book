from abc import ABC, abstractmethod
 
class Engine(ABC):
 
    def __init__(self):
        super().__init__()
    
    # query: CausalQuery, graph: Graph, config: EngineConfiguration
    # returns bool
    @abstractmethod
    def canCompute(self, query, graph, config = None):
        pass

    # 
    # returns Expression | Failure<Any>
    @abstractmethod
    def compute(self, query, graph, config = None):
        pass

    # returns Trace
    @abstractmethod
    def getTrace(self):
        pass

    # returns Dict[str, AlgorithmTracer]
    @abstractmethod
    def getAlgorithmTracers(self):
        pass