class Variable():

    name = str
    label = str

    def __init__(self, name = None, label = None):
        self.name = name
        self.label = label

def getName(v):
    return v.name if isinstance(v, Variable) else v