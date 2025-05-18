from src.graph_analysis.classes.probability_expression import ProbabilityExpression


class DoCalculusInspectionQuery():

    rule: int
    P: ProbabilityExpression

    def __init__(self, rule = 1, P = None):
        self.rule = rule
        self.P = P