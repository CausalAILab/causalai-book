from typing import List, Dict, Any

from src.graph.classes.graph_defs import NodeType, nodeTypeMap
from src.intervention.classes.intervention_type import InterventionType


class Intervention():

    node: Dict[str, Any]
    target: Dict[str, Any]
    type_: InterventionType
    inputParents: List[Dict[str, Any]]

    def __init__(self, node = None, target = None, type_ = InterventionType.idle, inputParents = None):
        self.node = node
        self.target = target
        self.type_ = type_
        self.inputParents = inputParents


interventionNodeType = NodeType('int', 'Intervention Strategy', 'INT')
nodeTypeMap[interventionNodeType.id_] = interventionNodeType