# ex) Backdoor, rule 2
# applicable: False
# expression: P(y|do(x))
# inference: P(y|x)
# independence: y \indep x in G_x_bar
# transformation: {over: [], under: [x]}

from typing import List

from src.inference.classes.expression import Expression
from src.graph_analysis.classes.transform_nodes import TransformNodes
from src.path_analysis.classes.path import Path


class DoCalculusInspectionResult():

    applicable: bool
    expression: Expression
    inference: Expression
    independence: Expression
    transformation: TransformNodes
    violating_paths: List[Path]

    def __init__(self, applicable = False, expression = None, inference = None, independence = None, transformation = TransformNodes(), violating_paths = []):
        self.applicable = applicable
        self.expression = expression
        self.inference = inference
        self.independence = independence
        self.transformation = transformation
        self.violating_paths = violating_paths