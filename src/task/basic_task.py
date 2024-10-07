from typing import List

from src.task.classes.task import Task, TaskSetDefinition
from src.task.classes.task_type import idTaskType

from src.common.uuid_generator import UUIDGenerator as uuid

treatmentDefName = 'treatment'
outcomeDefName = 'outcome'
adjustedDefName = 'adjusted'

treatmentDef = TaskSetDefinition(treatmentDefName, 'Treatment')
outcomeDef = TaskSetDefinition(outcomeDefName, 'Outcome')
adjustedDef = TaskSetDefinition(adjustedDefName, 'Adjusted')


class BasicTask(Task):

    def __init__(self):
        defs = [treatmentDef, outcomeDef, adjustedDef]
        sets = {}

        for df in defs:
            sets[df.name] = []

        super().__init__(type_ = idTaskType.id_, definitions = defs, sets = sets)


    def add(self, df, sets):
        return

#     add(definition: TaskSetDefinition, sets: (string | Variable)[]) {
#         if (!definition) return;

#         this.definitions.push(definition);
#         this.sets[definition.name] = sets;
#     }

    def update(self, defName, sets):
        return

#     update(defName: string, sets: (string | Variable)[]) {
#         if (!defName) return;

#         this.sets[defName] = sets;
#     }

    def updateCollection(self, defName, collections):
        return

#     updateCollection(defName: string, collections: (string | Variable)[][]) {
#         if (!defName) return;

#         this.collections[defName] = collections;
#     }

    def delete(self, defName):
        return

#     delete(defName: string) {
#         if (!defName) return;

#         for (let i = this.definitions.length - 1; i >= 0; i--) {
#             let def: TaskSetDefinition = this.definitions[i];

#             if (defName == def.name)
#                 this.definitions.splice(i, 1);
#         }

#         delete this.sets[defName];
#     }
# }