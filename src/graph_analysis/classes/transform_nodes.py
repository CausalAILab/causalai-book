from typing import List, Dict, Any

class TransformNodes():

    over: List[Dict[str, Any]]
    under: List[Dict[str, Any]]
    overExcept: List[Dict[str, Any]]
    underExcept: List[Dict[str, Any]]

    def __init__(self, over = [], under = [], overExcept = [], underExcept = []):
        self.over = over
        self.under = under
        self.overExcept = overExcept
        self.underExcept = underExcept