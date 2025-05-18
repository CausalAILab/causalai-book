from src.transportability.classes.transportability import transportabilityNodeType
from src.inference.classes.expression import Expression

from src.inference.utils.set_utils import SetUtils as su


class TransportabilityUtils():

    # /**
    #  * Lists the selection nodes in a given selection diagram for a specific population
    #  * @param D A selection diagram
    #  * @param population A population to get S-nodes from
    #  * @returns The set of S-nodes associated with the given population in the given selection diagram
    #  */
    # Graph, Population
    # Node[]
    @staticmethod
    def getSelectionNodesFor(D, population):
        nodes = []

        for node in D.nodes:
            if node['type_'] != transportabilityNodeType.id_:
                continue

            if 'metadata' in node and 'populations' in node['metadata'] and population.id_ in node['metadata']['populations']:
                nodes.append(node)

        return nodes


#     static subGraphWithTRNodes(subgraph: Node[], D: Graph): Graph {
#         let trNodesInD = D.nodes.filter((n) => n.type == transportabilityNodeType.id);
#         let Ds = gu.minus(D, su.difference(D.nodes, su.union(subgraph, trNodesInD), 'name'), true);
#         let reachable = gu.reach(subgraph, Ds, directedEdgeType, Direction.backward);
#         let trNodes = reachable.filter((n) => n.type == transportabilityNodeType.id);
#         return gu.minus(D, su.difference(D.nodes, su.union(subgraph, trNodes), 'name'), true);
#     }

    # Expression, any[], Population
    # Expression


    @staticmethod
    def setScripts(P, I, domain):
        if not isinstance(P, Expression) or P.type_ is None:
            return P

        if P.type_ == 'prob':
            if su.isEmpty(su.difference(P.parts[0], I, 'name')):
                return None

            # subscript
            if I is not None and len(I) > 0:
                if P.parts[2] is None:
                    P.parts[2] = I
                else:
                    P.parts[2] = su.union(P.parts[2], I, 'name')

            # superscript
            if domain is not None:
                if len(P.parts) == 1:
                    P.parts.append(None)

                if len(P.parts) == 2:
                    P.parts.append(None)

                if len(P.parts) == 3:
                    P.parts.append(None)

                P.parts[3] = domain.label

            return P

        else:
            if P.parts is not None and len(P.parts) > 0:
                for i in range(len(P.parts)):
                    P.parts[i] = TransportabilityUtils.setScripts(
                        P.parts[i], I, domain)

            return P


#     static getShortenedPopulationLabel(name: string): string {
#         return name.split(' ').map((word: string) => { return word.charAt(0).toUpperCase() }).join('');
#     }
# }
