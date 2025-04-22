from typing import Dict, Any

# from graph.classes.graph_defs import latentNodeType, directedEdgeType, bidirectedEdgeType

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import latentNodeType, directedEdgeType, bidirectedEdgeType

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su


class ProjectionUtils():


    # Graph
    # Graph
    @staticmethod
    def projectOverNonLatentNodes(G):
        if not G:
            return None

        V = list(filter(lambda n: n['type_'] != latentNodeType.id_, G.nodes))

        graph = ProjectionUtils.projectOver(G, V)

        return graph


    # Graph, Node[]
    # Graph
    @staticmethod
    def projectOver(G, V):
        if not G:
            return None
        
        if not V or len(V) == 0:
            return Graph()

        # nodes may not belong to the given graph
        # so map the nodes in G by each node name
        V = list(map(lambda n: gu.getNodeByName(n['name'], G), V))
        V = list(filter(lambda n: n is not None, V))

        graph = G.copy()

        # # remove nodes not in V
        # remaining = su.difference(graph.nodes, V, 'name')

        # graph.deleteNodes(remaining)

        orderedV = gu.topoSort(graph)
        latentsInOrder = list(filter(lambda n: n['type_'] == latentNodeType.id_, orderedV))
        
        for latent in latentsInOrder:
            # step 3
            parents = gu.filterBasicNodes(gu.parents(latent, graph), False)
            children = gu.filterBasicNodes(gu.children(latent, graph), False)

            for parent in parents:
                for child in children:
                    dirPtoC = gu.getEdgeByName(parent['name'], child['name'], graph, directedEdgeType)

                    # add latent nodes/edges info to new edge metadata
                    dirPtoL = gu.getEdgeByName(parent['name'], latent['name'], graph, directedEdgeType)
                    dirLtoC = gu.getEdgeByName(latent['name'], child['name'], graph, directedEdgeType)

                    dirPtoLinG = gu.getEdgeByName(parent['name'], latent['name'], G, directedEdgeType)
                    dirLtoCinG = gu.getEdgeByName(latent['name'], child['name'], G, directedEdgeType)

                    edgeToOperate = None

                    # if edge already exists, add latent nodes/edges info to metadata
                    if dirPtoC:
                        edgeToOperate = dirPtoC
                    else:
                        edge = {
                            'from_': parent['name'], 'to_': child['name'], 'type_': directedEdgeType.id_, 'metadata': {
                                'directedLatentPath': True
                                # necessary?
                                # , 'latentNodeIds': [], 'latentEdgeIds': []
                            }
                        }

                        graph.addEdges(edge)

                        edgeToOperate = edge
                    
                    if not edgeToOperate['metadata']:
                        edgeToOperate['metadata'] = {}

            # step 4
            incidentBidirected = list(filter(lambda e: e['type_'] == bidirectedEdgeType.id_, gu.getIncoming(latent, graph)))
            incidentNodesViaBidirected = []

            for edge in incidentBidirected:
                fromNode = gu.getNodeByName(edge['from_'], graph)
                toNode = gu.getNodeByName(edge['to_'], graph)

                if fromNode['name'] is not latent['name']:
                    incidentNodesViaBidirected.append(fromNode)
                elif toNode['name'] is not latent['name']:
                    incidentNodesViaBidirected.append(toNode)

            incidentNodes = su.union(children, incidentNodesViaBidirected, 'name')
            pairs = ou.pairs(incidentNodes, True)
            
            for pair in pairs:
                X = pair[0]
                Y = pair[1]

                dirLtoX = gu.getEdgeByName(latent['name'], X['name'], graph, directedEdgeType)
                dirLtoY = gu.getEdgeByName(latent['name'], Y['name'], graph, directedEdgeType)
                biLX = gu.getEdgeByName(latent['name'], X['name'], graph, bidirectedEdgeType)
                biLY = gu.getEdgeByName(latent['name'], Y['name'], graph, bidirectedEdgeType)

                if not biLX:
                    biLX = gu.getEdgeByName(X['name'], latent['name'], graph, bidirectedEdgeType)

                if not biLY:
                    biLY = gu.getEdgeByName(Y['name'], latent['name'], graph, bidirectedEdgeType)

                # X <-> L -> Y
                case1 = biLX is not None and dirLtoY is not None
                # X <- L <-> Y
                case2 = dirLtoX is not None and biLY is not None
                # X <- L -> Y
                case3 = dirLtoX is not None and dirLtoY is not None

                if case1 or case2 or case3:
                    biXY = gu.getEdgeByName(X['name'], Y['name'], graph, bidirectedEdgeType)
                    biYX = gu.getEdgeByName(Y['name'], X['name'], graph, bidirectedEdgeType)

                    # if edge already exists, add latent nodes/edges info to metadata
                    if biXY is not None or biYX is not None:
                        continue

                    edge = {
                        'from_': X['name'], 'to_': Y['name'], 'type_': bidirectedEdgeType.id_, 'metadata': {}
                    }

                    graph.addEdges(edge)

            graph.deleteNodes(latent)

        return graph


    # Graph
    # Graph
    @staticmethod
    def unproject(G):
        if not G:
            return G

        graph = G.copy()
        
        bidirectedEdges = list(filter(lambda e: e['type_'] == bidirectedEdgeType.id_, graph.edges))
        
        latentNodes = []
        latentEdges = []
        
        for edge in bidirectedEdges:
            nodeInfo = ProjectionUtils.bidirectedEdgeToLatentNode(edge, G)
            
            if nodeInfo is None:
                continue

            latentNodes.append(nodeInfo.node)
            latentEdges.append(nodeInfo.fromEdge)
            latentEdges.append(nodeInfo.toEdge)
        
        graph.deleteEdges(bidirectedEdges)
        
        graph.addNodes(latentNodes)
        graph.addEdges(latentEdges)

        return graph


    # Edge, Graph
    # BidirectedEdgeInfo
    @staticmethod
    def bidirectedEdgeToLatentNode(edge, G):
        if not edge or edge['type_'] != bidirectedEdgeType.id_:
            return None
        
        latentNodeName = 'U'
        
        fromComesFirst = edge['from_'] < edge['to_']

        if fromComesFirst:
            # latentNodeName += '_{' + edge.from + '' + edge.to + '}'
            latentNodeName = ''.join(['U_{', edge['from_'], edge['to_'], '}'])
        else:
            # latentNodeName += '_{' + edge.to + '' + edge.from + '}'
            latentNodeName = ''.join(['U_{', edge['to_'], edge['from_'], '}'])

        latentNode = {
            'name': latentNodeName,
            'type_': latentNodeType.id_,
        }
        fromEdge = {
            'from_': latentNodeName,
            'to_': edge['from_'],
            'type_': directedEdgeType.id_
        }
        toEdge = {
            'from_': latentNodeName,
            'to_': edge['to_'],
            'type_': directedEdgeType.id_
        }

        return BidirectedEdgeInfo(latentNode, fromEdge, toEdge)


class BidirectedEdgeInfo():

    node = Dict[str, Any]
    fromEdge = Dict[str, Any]
    toEdge = Dict[str, Any]

    def __init__(self, node, fromEdge, toEdge):
        self.node = node
        self.fromEdge = fromEdge
        self.toEdge = toEdge