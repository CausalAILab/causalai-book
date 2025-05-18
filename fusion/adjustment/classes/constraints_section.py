import re

from src.graph.classes.graph_defs import basicNodeType
from src.task.basic_task import treatmentDefName, outcomeDefName
from src.adjustment.classes.constraints_task import constraintsIDefName, constraintsRDefName, constraintsIDef, constraintsRDef
from src.editor.classes.section import Section
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su


# Regex for parsing constraints settings
#            label                      list
#  /^       ([^\s]+)     \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

errors = {
    'parse': 'Please specify the constraints in correct format.',
    'constraints': 'Please specify \'I\' or \'R\' as a constraint.',
    'Ifirst': 'Please specify \'I\' constraints before \'R\'.',
    'IinR': '\'I\' must be a subset or equal to \'R\'.',
    'treatmentInI': '\'I\' cannot include treatment variable(s).',
    'outcomeInI': '\'I\' cannot include outcome variable(s).',
    'treatmentInR': '\'R\' cannot include treatment variable(s).',
    'outcomeInR': '\'R\' cannot include outcome variable(s).',
    'graphTagMissing': 'Please specify the nodes and edges before the constraints section.',
    'taskTagMissing': 'Please provide the tasks before the constraints section.'
}


class ConstraintsSection(Section):

    tag = '<CONSTRAINTS>'
    required = False
    order = 8

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)

    def parse(self, lines, parsedData={}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        if 'task' not in parsedData:
            return ParsingError(errors['taskTagMissing'])

        graph = parsedData['graph']
        task = parsedData['task']

        lineNumber = 0

        try:
            for line in lines:
                constraints = self.constraintsFromString(line, graph, task)

                if constraints['label'] == constraintsIDefName:
                    task.sets[constraintsIDefName] = constraints['names']

                    taskDef = None

                    for df in task.definitions:
                        if df.name == constraintsIDefName:
                            taskDef = df
                            break

                    if taskDef is None:
                        task.definitions.append(constraintsIDef)
                elif constraints['label'] == constraintsRDefName:
                    task.sets[constraintsRDefName] = constraints['names']

                    taskDef = None

                    for df in task.definitions:
                        if df.name == constraintsRDefName:
                            taskDef = df
                            break

                    if taskDef is None:
                        task.definitions.append(constraintsRDef)

                lineNumber = lineNumber + 1

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

    def getLines(self):
        return []

    def destroy(self):
        pass

    # str, Graph, Task

    def constraintsFromString(self, line, graph, task):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        paramName = groups[0]
        listText = groups[1]

        if paramName is None or paramName.strip() == '':
            raise ParsingError(errors['parse'])

        paramName = paramName.strip()

        if paramName != constraintsIDefName and paramName != constraintsRDefName:
            raise ParsingError(errors['constraints'])

        nodeNames = list(
            filter(lambda n: n is not None and n != '', listText.split(',')))
        nodes = list(filter(
            lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(nodeNames, graph)))

        XNames = task.sets[treatmentDefName]
        YNames = task.sets[outcomeDefName]
        X = gu.getNodesByName(XNames, graph)
        Y = gu.getNodesByName(YNames, graph)

        if len(su.intersection(nodes, X, 'name')) > 0:
            if paramName == constraintsIDefName:
                raise ParsingError(errors['treatmentInI'])
            elif paramName == constraintsRDefName:
                raise ParsingError(errors['treatmentInR'])

        if len(su.intersection(nodes, Y, 'name')) > 0:
            if paramName == constraintsIDefName:
                raise ParsingError(errors['outcomeInI'])
            elif paramName == constraintsRDefName:
                raise ParsingError(errors['outcomeInR'])

        # I \subseteq R must hold
        if paramName == constraintsRDefName:
            if constraintsIDefName not in task.sets:
                raise ParsingError(errors['Ifirst'])

            Inames = task.sets[constraintsIDefName]
            Inodes = list(filter(
                lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(Inames, graph)))

            if not (su.isSubset(Inodes, nodes, 'name') or su.equals(Inodes, nodes, 'name')):
                raise ParsingError(errors['IinR'])

        return {'label': paramName, 'names': nodeNames}
