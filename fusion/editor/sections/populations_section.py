import re
from typing import Dict

from src.graph.classes.graph import Graph
from src.task.classes.task import TaskSetDefinition
from src.task.basic_task import BasicTask
from src.transportability.classes.population import Population
from src.transportability.classes.transportability import targetPopulation
from src.transportability.classes.transportability_task import experimentFieldSuffix, observedFieldSuffix
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing population strings
#      label          name
#  /^  ([^\s]+) \s* : \s*   (.+)   \s*$/
# regexExp = r'^([^\s]+)\s*:\s*(.+)\s*$'
regexExp = r'^([^\s]+)\s*:\s*(.+)\s*$'

errors = {
    'parse': 'Please specify a population in correct format.'
}


class PopulationsSection(Section):

    tag = '<POPULATIONS>'
    required = False
    order = 1

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)

    def parse(self, lines, parsedData={}):
        if 'graph' not in parsedData:
            parsedData['graph'] = Graph()

        if 'task' not in parsedData:
            parsedData['task'] = BasicTask()

        graph = parsedData['graph']
        task = parsedData['task']
        graph.metadata['populations'] = []

        lineNumber = 0

        try:
            for line in lines:
                population = self.populationFromString(line)
                graph.metadata['populations'].append(population)

                lineNumber = lineNumber + 1

            found = False

            for pop in graph.metadata['populations']:
                if pop.label == targetPopulation.label:
                    found = True
                    break

            if not found:
                graph.metadata['populations'].insert(0, targetPopulation)

            # update task
            for pop in graph.metadata['populations']:
                expField = pop.label + experimentFieldSuffix
                obsField = pop.label + observedFieldSuffix

                expFilter = list(filter(lambda df: df.name ==
                                 expField, task.definitions))

                if len(expFilter) == 0:
                    taskDef = TaskSetDefinition(
                        expField, 'Z^{' + pop.label + '}')
                    task.definitions.append(taskDef)
                    task.sets[expField] = []

                if expField not in task.collections:
                    task.collections[expField] = []

                if len(task.collections[expField]) == 0:
                    if expField in task.sets:
                        task.collections[expField].append(task.sets[expField])
                    else:
                        task.collections[expField].append([])

                obsFilter = list(filter(lambda df: df.name ==
                                 obsField, task.definitions))

                if len(obsFilter) == 0:
                    taskDef = TaskSetDefinition(
                        obsField, 'P^{' + pop.label + '}(v)')
                    task.definitions.append(taskDef)
                    task.sets[obsField] = []

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

    def getLines(self):
        return []

    def destroy(self):
        pass

    def populationFromString(self, line):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        label = groups[0]
        name = groups[1]

        if not name or not label or name.strip() == '' or label.strip() == '':
            raise ParsingError(errors['parse'])

        return Population(name, label)
