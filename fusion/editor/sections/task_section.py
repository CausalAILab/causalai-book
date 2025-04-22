import re

from src.graph.classes.graph_defs import basicNodeType
from src.task.basic_task import BasicTask, treatmentDef, outcomeDef, adjustedDef, treatmentDefName, outcomeDefName, adjustedDefName
from src.intervention.classes.intervention import Intervention, InterventionType, interventionNodeType
from src.intervention.classes.intervention_task import interventionDef, interventionDefName
from src.transportability.classes.transportability import targetPopulation
from src.editor.classes.section import Section
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing task sets
#       definition                 list
#  /^   ([^\s]+)   \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

# Regex for parsing interventions
#      node names      intv type     input parents
#  /^   ([^\s]+)       \s*([^\s]+)   \s*(.*)? $/
invRegexExp = r'^([^\s]+)\s*([^\s]+)\s*(.*)?$'

errors = {
    'parse': 'Please specify a task in correct format.',
    'intervention': 'Please specify interventions in correct format.',
    'interventionNodeNonExist': 'Please specify interventions in correct format.',
    'interventionNotInTreatment': 'Please specify interventions in correct format.',
    'interventionType': 'Please specify one of the following intervention types: idle, atomic, conditional, or stochastic.',
    'graphTagMissing': 'Please specify the nodes and edges before the task\'s section.'
}


class TaskSection(Section):

    tag = '<TASK>'
    required = False
    order = 4

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.regexExp = re.compile(regexExp)
        self.invRegexExp = re.compile(invRegexExp)

    def parse(self, lines, parsedData={}):
        if parsedData is None or 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        graph = parsedData['graph']
        task = BasicTask()

        lineNumber = 0

        try:
            for line in lines:
                taskSet = self.setFromString(line, graph, task)

                if taskSet['def'].name in [treatmentDefName, outcomeDefName, adjustedDefName, interventionDefName]:
                    task.sets[taskSet['def'].name] = taskSet['list']

                lineNumber = lineNumber + 1

            parsedData['task'] = task

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

    def getLines(self):
        return []

    def destroy(self):
        pass

    def setFromString(self, line, graph, task):
        match = self.regexExp.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        defText = groups[0]
        listText = groups[1]

        definition = self.getTaskDefinition(defText)

        if definition is None:
            raise ParsingError("The task '" + defText + "' is not supported.")

        if definition == interventionDef:
            intvs = []
            intvTokens = [l.strip() for l in listText.split(';')]

            for token in intvTokens:
                match = self.invRegexExp.match(token)

                if match is None:
                    raise ParsingError(errors['intervention'])

                groups = match.groups()

                nodeName = groups[0]
                intvType = groups[1]

                targetNode = gu.getNodeByName(nodeName, graph)

                if targetNode is None:
                    raise ParsingError(errors['interventionNodeNonExist'])

                # check if target node pointed by sigma node is specifed in task.treatment
                # treatmentNodeNames = task.sets[treatmentDefName]

                # if targetNode['name'] not in treatmentNodeNames:
                #     raise ParsingError(errors['interventionNotInTreatment'])

                if intvType not in ['idle', 'atomic', 'conditional', 'stochastic']:
                    raise ParsingError(errors['interventionType'])

                sigmaNode = {'name': '\\sigma_' + targetNode['name'], 'type_': interventionNodeType.id_, 'metadata': {
                    'populations': [targetPopulation.id_]}}

                intv = Intervention()
                intv.node = sigmaNode
                intv.target = targetNode
                intv.type_ = self.toInterventionType(intvType)

                if intv.type_ == InterventionType.conditional or intv.type_ == InterventionType.stochastic:
                    if len(groups) > 2:
                        inputParentsText = groups[2]
                        names = list(filter(lambda n: n is not None and n !=
                                            '', inputParentsText.split(',')))
                        nodes = gu.getNodesByName(names, graph)

                        if len(names) != len(nodes):
                            raise ParsingError(errors['intervention'])

                        intv.inputParents = nodes

                intvs.append(intv)

            return {'def': definition, 'list': intvs}
        else:
            # parse variables
            names = list(filter(lambda n: n is not None and n !=
                                '', listText.split(',')))
            nodes = list(filter(
                lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(names, graph)))
            names = list(map(lambda n: n['name'], nodes))

            return {'def': definition, 'list': names}

    def getTaskDefinition(self, name):
        filterDef = list(filter(lambda t: t.name == name, [
                         treatmentDef, outcomeDef, adjustedDef, interventionDef]))

        if len(filterDef) > 0:
            return filterDef[0]
        else:
            return None

    def toInterventionType(self, val):
        if val == 'idle':
            return InterventionType.idle
        elif val == 'atomic':
            return InterventionType.atomic
        elif val == 'conditional':
            return InterventionType.conditional
        elif val == 'stochastic':
            return InterventionType.stochastic
