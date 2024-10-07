import re

from src.intervention.classes.intervention import Intervention, InterventionType
from src.intervention.classes.intervention_task import interventionFieldSuffix
from src.transportability.classes.transportability import targetPopulation
from src.task.classes.task import TaskSetDefinition
from src.editor.classes.section import Section
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing experiment definitions
#      population label             list
#  /^       ([^\s]+)     \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

# Regex for parsing interventions
#      node names      intv type     input parents
#  /^   ([^\s]+)       \s*([^\s]+)   \s*(.*)? $/
intvRegexExp = r'^([^\s]+)\s*([^\s]+)\s*(.*)?$'

errors = {
    'parse': 'Please specify interventions in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the query\'s section.',
    'intervention': 'Please specify interventions in correct format.',
    'interventionType': 'Please specify one of the following intervention types: idle, atomic, conditional, or stochastic.',
    'name': 'Please specify the name of the node.'
}


class InterventionsSection(Section):

    tag = '<INTERVENTIONS>'
    required = False
    order = 7

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)
        self.intvRegexExp = re.compile(intvRegexExp)

    def parse(self, lines, parsedData={}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        if 'task' not in parsedData:
            return ParsingError(errors['taskTagMissing'])

        graph = parsedData['graph']
        task = parsedData['task']
        populations = graph.metadata['populations'] if 'populations' in graph.metadata else [
            targetPopulation]
        # collection of interventions
        # assumption: the order follows the one of populations
        interventions = []
        interventionSpecs = {}

        lineNumber = 0

        try:
            for line in lines:
                intvsObj = self.intvsFromString(line, graph, populations)
                popLabel = intvsObj['label']
                intvs = intvsObj['interventions']
                intvDefName = popLabel + interventionFieldSuffix

                # add interventions (related to one population) to a task
                taskDef = None

                for df in task.definitions:
                    if df.name == intvDefName:
                        taskDef = df
                        break

                if taskDef is None:
                    taskDef = TaskSetDefinition(
                        intvDefName, 'Z^{' + popLabel + '}')
                    task.definitions.append(taskDef)

                task.sets[intvDefName] = intvs

                if intvDefName in task.collections:
                    task.collections[intvDefName][0] = intvs
                else:
                    task.collections[intvDefName] = [intvs]

                lineNumber = lineNumber + 1

            # assumes 1 collection of exps
            for pop in populations:
                intvDefName = pop.label + interventionFieldSuffix

                if intvDefName in task.sets:
                    intvs = task.sets[intvDefName]
                    interventionSpecs[pop.label] = [intvs]

            for pop in populations:
                interventions.append(interventionSpecs[pop.label])

            parsedData['interventions'] = interventions
            parsedData['interventionSpecs'] = interventionSpecs

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

    def getLines(self):
        return []

    def destroy(self):
        pass

    def intvsFromString(self, line, graph, populations):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        popLabel = groups[0]
        listText = groups[1]

        if popLabel is None or popLabel.strip() == '':
            raise ParsingError(errors['parse'])

        popLabel = popLabel.strip()

        # check if population exists
        population = None

        for p in populations:
            if p.label == popLabel:
                population = p
                break

        if population is None:
            raise ParsingError(errors['population'])

        # parse the list of interventions
        intvs = []
        intvTokens = [l.strip() for l in listText.split(';')]

        for token in intvTokens:
            if token == '':
                continue

            match = self.intvRegexExp.match(token)

            if match is None:
                raise ParsingError(errors['intervention'])

            groups = match.groups()

            nodeName = groups[0]
            intvType = groups[1]

            sigmaNode = gu.getNodeByName(nodeName, graph)

            if sigmaNode is None:
                raise ParsingError(errors['interventionNodeNonExist'])

            if intvType not in ['idle', 'atomic', 'conditional', 'stochastic']:
                raise ParsingError(errors['interventionType'])

            # find a target by looking at an edge sigma_node -> target
            targets = gu.children(sigmaNode, graph)
            target = targets[0]

            intv = Intervention()
            intv.node = sigmaNode
            intv.target = target
            intv.type_ = self.toInterventionType(intvType)
            # metadata: add population info

            if intv.type_ == InterventionType.conditional or intv.type_ == InterventionType.stochastic:
                if len(groups) > 2:
                    inputParentsText = groups[2]
                    names = list(filter(lambda n: n is not None and n !=
                                        '', inputParentsText.split(',')))
                    nodes = gu.getNodesByName(names, graph)

                    if len(names) != len(nodes):
                        raise ParsingError(errors['name'])

                    intv.inputParents = nodes

            intvs.append(intv)

        return {'label': popLabel, 'interventions': intvs}

    def toInterventionType(self, val):
        if val == 'idle':
            return InterventionType.idle
        elif val == 'atomic':
            return InterventionType.atomic
        elif val == 'conditional':
            return InterventionType.conditional
        elif val == 'stochastic':
            return InterventionType.stochastic
