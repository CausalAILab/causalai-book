from abc import ABC, abstractmethod
from numbers import Number

class Section(ABC):

    tag = str
    required = bool
    order = Number
    
    def __init__(self):
        super().__init__()

    @abstractmethod
    def parse(self, lines, parsedData):
        pass

    @abstractmethod
    def getLines(self):
        pass

    @abstractmethod
    def destroy(self):
        pass