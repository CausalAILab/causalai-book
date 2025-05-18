from abc import ABC, abstractmethod


class OptionsParser(ABC):

    def __init__(self):
        super().__init__()

    # NodeType | EdgeType
    @abstractmethod
    def getType(self):
        pass

    # T, Graph
    # str
    @abstractmethod
    def toString(self, target, graph):
        pass

    # str, T, Graph
    @abstractmethod
    def fromString(self, text, target, graph):
        pass