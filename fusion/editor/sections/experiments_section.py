import re
from typing import Dict

from src.graph.classes.graph_defs import basicNodeType
from src.task.classes.task import TaskSetDefinition
from src.transportability.classes.transportability import targetPopulation
from src.transportability.classes.transportability_task import experimentFieldSuffix
from src.editor.classes.section import Section
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing experiment definitions
#      population label             list
#  /^       ([^\s]+)     \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

errors = {
    'population': 'Please specify a valid population.',
    'experiment': 'Please specify a valid experiment.',
    'parse': 'Please specify an experiment in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the experiment\'s section.',
    'taskTagMissing': 'Please provide the tasks before the experiment\'s section.',
    'name': 'Please specify the name of the node.'
}

class ExperimentsSection(Section):

    tag = '<EXPERIMENTS>'
    required = False
    order = 6

    def __init__(self, optTypeMap = {}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)


    def parse(self, lines, parsedData = {}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        if 'task' not in parsedData and 'counterfactuals' not in parsedData:
            return ParsingError(errors['taskTagMissing'])

        graph = parsedData['graph']
        task = parsedData['task']
        populations = graph.metadata['populations'] if 'populations' in graph.metadata else [targetPopulation]
        experiments = []
        experimentSpecs = {}

        lineNumber = 0

        try:
            for line in lines:
                exps = self.experimentsFromString(line, graph, populations)
                expDefName = exps['label'] + experimentFieldSuffix

                # update task
                taskDef = None

                for df in task.definitions:
                    if df.name == expDefName:
                        taskDef = df
                        break

                if taskDef is None:
                    taskDef = TaskSetDefinition(expDefName, 'Z^{' + exps['label'] + '}')
                    task.definitions.append(taskDef)

                task.sets[expDefName] = exps['names']

                nodes = gu.getNodesByName(exps['names'], graph)

                if expDefName in task.collections:
                    task.collections[expDefName][0] = nodes
                else:
                    task.collections[expDefName] = [nodes]

                lineNumber = lineNumber + 1

            # assumes 1 collection of exps
            for pop in populations:
                expDefName = pop.label + experimentFieldSuffix

                if expDefName in task.sets:
                    expNodeNames = task.sets[expDefName]
                    experimentSpecs[pop.label] = [gu.getNodesByName(expNodeNames, graph)]

            for pop in populations:
                experiments.append(experimentSpecs[pop.label])

            parsedData['experiments'] = experiments
            parsedData['experimentSpecs'] = experimentSpecs
            
            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

        return parsedData


    def getLines(self):
        return []


    def destroy(self):
        pass


    # str, Graph, Population[]
    def experimentsFromString(self, line, graph, populations):
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
        names = list(filter(lambda n: n is not None and n != '', listText.split(',')))
        nodes = list(filter(lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(names, graph)))

        if len(names) != len(nodes):
            raise ParsingError(errors['name'])

        names = list(map(lambda n: n['name'], nodes))

        return {'label': label, 'names': names}