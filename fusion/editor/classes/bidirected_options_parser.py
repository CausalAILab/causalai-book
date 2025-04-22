from src.editor.classes.options_parser import OptionsParser
from src.graph.classes.graph_defs import bidirectedEdgeType


class BidirectedOptionsParser(OptionsParser):

    def getType(self):
        return bidirectedEdgeType


    def toString(self, target, graph):
        return ''

    # toString(target: Edge, graph: Graph): string {
    #     if (target.metadata && target.metadata.latentId && graph.metadata && graph.metadata.annotations && graph.metadata.annotations[target.metadata.latentId]) {
    #         let mt = graph.metadata.annotations[target.metadata.latentId].metadata;
    #         return mt.label || mt.name;
    #     }

    #     return null;
    # }

    def fromString(self, text, target, graph):
        pass

    # fromString(str: string, target: Edge, graph: Graph): void {
    #     if (target && target.metadata && str && str.trim() != '')
    #         target.metadata.latentName = str.trim();
    # }