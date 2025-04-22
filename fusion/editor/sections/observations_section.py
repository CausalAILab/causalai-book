import re

# from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import basicNodeType
from src.task.classes.task import TaskSetDefinition
from src.transportability.classes.transportability import targetPopulation
from src.transportability.classes.transportability_task import observedFieldSuffix
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing observation settings
#      population label             list
#  /^       ([^\s]+)     \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

errors = {
    'parse': 'Please specify observations in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the observation\'s section.',
    'taskTagMissing': 'Please provide the tasks before the observation\'s section.'
}


class ObservationsSection(Section):

    tag = '<OBSERVATIONS>'
    required = False
    order = 7

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)

    def parse(self, lines, parsedData={}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        if 'task' not in parsedData and 'counterfactuals' not in parsedData:
            return ParsingError(errors['taskTagMissing'])

        graph = parsedData['graph']
        task = parsedData['task']
        populations = graph.metadata['populations'] if 'populations' in graph.metadata else [
            targetPopulation]
        observationSpecs = {}

        lineNumber = 0

        try:
            for line in lines:
                observations = self.observationsFromString(
                    line, graph, populations)
                obsDefName = observations['label'] + observedFieldSuffix

                # update task
                taskDef = None

                for df in task.definitions:
                    if df.name == obsDefName:
                        taskDef = df
                        break

                if taskDef is None:
                    taskDef = TaskSetDefinition(
                        obsDefName, 'P^{' + observations['label'] + '}(v)')
                    task.definitions.append(taskDef)

                task.sets[obsDefName] = observations['names']

                lineNumber = lineNumber + 1

            for pop in populations:
                obsDefName = pop.label + observedFieldSuffix

                if obsDefName in task.sets:
                    obsNodeNames = task.sets[obsDefName]
                    observationSpecs[pop.label] = gu.getNodesByName(
                        obsNodeNames, graph)

            parsedData['observationSpecs'] = observationSpecs

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

        return parsedData

    def getLines(self):
        return []

    def destroy(self):
        pass

    # str, Graph, Population[]

    def observationsFromString(self, line, graph, populations):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        label = groups[0]
        listText = groups[1]

        if label is None or label.strip() == '':
            raise ParsingError(errors['parse'])

        label = label.strip()

        population = None

        for pop in populations:
            if pop.label == label:
                population = pop
                break

        if population is None:
            raise ParsingError(errors['population'])

        # parse experiments
        names = list(filter(lambda n: n is not None and n !=
                     '', listText.split(',')))
        nodes = list(filter(
            lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(names, graph)))

        # throw error if name doesn't correspond to node

        names = list(map(lambda n: n['name'], nodes))

        return {'label': label, 'names': names}
