from enum import Enum

class InterventionType(Enum):
    idle = 0
    atomic = 1
    conditional = 2
    stochastic = 3