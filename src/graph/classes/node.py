# from inference.classes.variable import Variable
# from graph.classes.graph-defs import basicNodeType

# class Node(Variable):

#     id_ = str
#     type_ = str
#     metadata = dict()

#     def __init__(self, id_ = None, name = None, label = None, type_ = basicNodeType.id, metadata = dict()):
#         # generate random
#         if id_ is None:
#             self.id_ = ''
        
#         self.type_ = type_
#         self.metadata = metadata

#         super().__init__(name, label)

# def isNode(node):
#     return isinstance(node, Node)