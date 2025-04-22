class TaskType():

    id_ = str
    name = str

    def __init__(self, id_ = None, name = None):
        self.id_ = id_
        self.name = name

idTaskType = TaskType('ID', 'Confounding bias')
recoverTaskType = TaskType('SB', 'Selection bias')
transportTaskType = TaskType('TR', 'Transportability')

taskTypesMap = dict()
taskTypesMap[idTaskType.id_] = idTaskType
taskTypesMap[recoverTaskType.id_] = recoverTaskType
taskTypesMap[transportTaskType.id_] = transportTaskType