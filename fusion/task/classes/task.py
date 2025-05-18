from typing import List, Dict

from src.task.classes.task_type import idTaskType
from src.common.uuid_generator import UUIDGenerator as uuid


class TaskSetDefinition():

    name = str
    label = str

    def __init__(self, name = None, label = None):
        self.name = name
        self.label = label


class Task():

    type_ = str
    definitions = List[TaskSetDefinition]
    sets = Dict[str, List[str]]
    collections = Dict[str, List[List[str]]]

    def __init__(self, type_ = idTaskType.id_, definitions = [], sets = {}, collections = {}):
        self.type_ = type_
        self.definitions = definitions
        self.sets = sets
        self.collections = collections