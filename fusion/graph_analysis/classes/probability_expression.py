from typing import List, Dict, Any


class ProbabilityExpression():

    X: List[Dict[str, Any]]
    Y: List[Dict[str, Any]]
    Z: List[Dict[str, Any]]
    W: List[Dict[str, Any]]

    def __init__(self, X = [], Y = [], Z = [], W = []):
        self.X = X
        self.Y = Y
        self.Z = Z
        self.W = W