from typing import List

from src.graph_analysis.classes.probability_expression import ProbabilityExpression
from src.intervention.classes.intervention import Intervention


class Interventions():

    X: List[Intervention]
    Z: List[Intervention]
    Zprime: List[Intervention]

    def __init__(self, X = [], Z = [], Zprime = []):
        self.X = X
        self.Z = Z
        self.Zprime = Zprime

class SigmaCalculusInspectionQuery():

    rule: int
    P: ProbabilityExpression
    interventions: Interventions

    def __init__(self, rule = 1, P = None, interventions = None):
        self.rule = rule
        self.P = P if P is not None else ProbabilityExpression()
        self.interventions = interventions if interventions is not None else Interventions()