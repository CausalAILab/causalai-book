from typing import List

from src.path_analysis.classes.path import Path


class SigmaCalculusSeparationResult():

    separable: bool
    paths: List[Path]

    def __init__(self, separable = False, paths = []):
        self.separable = separable
        self.paths = paths