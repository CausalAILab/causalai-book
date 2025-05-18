from src.intervention.classes.intervention import interventionNodeType
from src.intervention.classes.intervention_type import InterventionType

from src.inference.utils.graph_utils import GraphUtils as gu, compareNames
from src.inference.utils.set_utils import SetUtils as su


class SigmaCalculusUtils():

    # Graph, Intervention[]
    # Graph
    @staticmethod
    def createGraphSigma(graph, intvs):
        if not graph:
            return None

        if not intvs:
            return graph

        G = gu.clone(graph)

        # filter intvs so that it adds sigma nodes whose target actually exists in graph
        subIntvs = list(filter(lambda intv: su.belongs(
            intv.target, graph.nodes, compareNames), intvs))

        for intv in subIntvs:
            nodeName = intv.target['name']

            sigmaNode = {
                'name': '\\sigma_' + nodeName if len(nodeName) == 1 else '\\sigma_{' + nodeName + '}',
                'type_': interventionNodeType.id_
            }

            sigmaToTarget = {
                'from_': sigmaNode['name'],
                'to_': nodeName
            }

            # remove all incoming to target (except sigmaToTarget)
            if intv.type_ == InterventionType.atomic:
                incomingEdges = gu.getIncoming(intv.target, G)

                G.deleteEdges(incomingEdges)

            # add input parent -> target
            # check for cycle
            elif intv.type_ == InterventionType.conditional or intv.type_ == InterventionType.stochastic:
                incomingEdges = gu.getIncoming(intv.target, G)

                G.deleteEdges(incomingEdges)

                for parent in intv.inputParents:
                    partentToTarget = {
                        'from_': parent['name'],
                        'to_': nodeName,
                    }

                    # warning: could add a cycle
                    G.addEdges(partentToTarget)

            G.addEdges(sigmaToTarget)

        # G.edges = EdgeUtils.unique(G.edges)

        return G
