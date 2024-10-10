from src.selection_bias.classes.selection_bias import selectionBiasNodeType
from src.transportability.classes.transportability import transportabilityNodeType

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su


class ComputeUtils():

    # Graph
    # Node
    @staticmethod
    def getSelectionBiasNode(G):
        if not G:
            return None
        
        nodes = list(filter(lambda n: n['type_'] == selectionBiasNodeType.id_, G.nodes))
        
        return nodes[0] if len(nodes) > 0 else None


    # Graph
    # Node[]
    @staticmethod
    def getSelectionNodes(G):
        if not G:
            return []

        return list(filter(lambda n: n['type_'] == transportabilityNodeType.id_, G.nodes))


    # Graph
    # boolean
    @staticmethod
    def inSBContext(G):
        S = ComputeUtils.getSelectionBiasNode(G)

        if S is None:
            return False

        reachableFromS = su.difference(gu.reach(S, G), [S], 'name')

        return len(reachableFromS) > 0