# from typing import List

# from inference.classes.variable import Variable
from src.common.object_utils import ObjectUtils as ou


class CausalQuery():

    # X: List[Variable]
    # Y: List[Variable]
    # Z: List[Variable]

    def __init__(self, x, y, z=[], interventions=[]):
        self.x = ou.makeArray(x)
        self.y = ou.makeArray(y)
        self.z = ou.makeArray(z)
        self.interventions = ou.makeArray(interventions)
