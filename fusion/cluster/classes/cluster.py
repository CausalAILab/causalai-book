from src.graph.classes.graph_defs import NodeType, nodeTypeMap

clusterNodeType = NodeType('cluster', 'Cluster', 'C')
nodeTypeMap[clusterNodeType.id_] = clusterNodeType