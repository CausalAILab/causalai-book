from src.graph.classes.graph_defs import NodeType, nodeTypeMap

selectionBiasNodeType = NodeType('sb', 'Selection Bias', 'SB')
nodeTypeMap[selectionBiasNodeType.id_] = selectionBiasNodeType