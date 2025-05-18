from src.editor.classes.options_parser import OptionsParser
from src.graph.classes.graph_defs import latentNodeType


class LatentOptionsParser(OptionsParser):

    def getType(self):
        return latentNodeType


    def toString(self, target, graph):
        return ''


    def fromString(self, text, target, graph):
        pass