from typing import List, Union

from src.inference.classes.variable import Variable


class Expression():

    type_: str
    # parts: List[Union[Expression, str, Variable, List[Union[Expression, str, Variable]]]]

    def __init__(self, type_, parts):
        self.type_ = type_
        self.parts = parts