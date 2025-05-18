from src.path_analysis.classes.direction import Direction as PathDirection


class PathEdge():

    # edge = Edge
    direction = PathDirection

    def __init__(self, edge, direction):
        self.edge = edge
        self.direction = direction

    @property
    def source(self):
        return self.edge['to_'] if self.direction == PathDirection.reversed else self.edge['from_']

    @property
    def target(self):
        return self.edge['to_'] if self.direction == PathDirection.directed else self.edge['from_']