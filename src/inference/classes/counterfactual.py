# from typing import List

# from inference.classes.variable import Variable
from src.common.object_utils import ObjectUtils as ou


class Counterfactual():

    # variable: Variable
    # value: number, str, bool
    # interventions: List[Intervention]

    def __init__(self, variable, value=None, interventions=[]):
        self.variable = variable
        self.value = value
        self.interventions = ou.makeArray(interventions)


class Intervention():

    # variable: Variable
    # value: number, str, bool, Counterfactual

    def __init__(self, variable, value=None):
        self.variable = variable
        self.value = value
