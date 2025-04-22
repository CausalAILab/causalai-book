import re

from src.intervention.classes.intervention import Intervention, InterventionType
from src.editor.classes.section import Section
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing interventions
#      node names      intv type     input parents
#  /^   ([^\s]+)   \s*  ([^\s]+)    \s*  (.*)? $/
regexExp = r'^([^\s]+)\s*([^\s]+)\s*(.*)?$'

errors = {
    'parse': 'Please specify interventions in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the query\'s section.',
    'name': 'Please specify the name of the node.'
    # 'rule': 'Please specify a valid rule (1, 2, or 3).'
}

treatment_current = 'treatment_current'
treatment_new = 'treatment_new'
interventional = 'interventional'


class SigmaCalculusInterventionsSection(Section):

    tag = '<INTERVENTIONS>'
    required = False
    order = 6

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)

    def parse(self, lines, parsedData={}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        graph = parsedData['graph']
        query = parsedData['query']
        sigmaX = []
        sigmaZ = []
        sigmaZprime = []

        lineNumber = 0
        currentTask = interventional

        try:
            for line in lines:
                intvObj = self.intvFromString(line, graph)

                if isinstance(intvObj, str):
                    currentTask = intvObj
                else:
                    if currentTask == treatment_current:
                        sigmaZ.append(intvObj)
                    elif currentTask == treatment_new:
                        sigmaZprime.append(intvObj)
                    elif currentTask == interventional:
                        sigmaX.append(intvObj)

                lineNumber = lineNumber + 1

            query.interventions.X = sigmaX
            query.interventions.Z = sigmaZ
            query.interventions.Zprime = sigmaZprime

            parsedData['interventions'] = sigmaX

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

    def getLines(self):
        return []

    def destroy(self):
        pass

    def intvFromString(self, line, graph):
        if line.strip() == treatment_current + ':':
            return treatment_current
        elif line.strip() == treatment_new + ':':
            return treatment_new
        elif line.strip() == interventional + ':':
            return interventional

        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        nodeName = groups[0]
        intvType = groups[1]

        node = gu.getNodeByName(nodeName, graph)

        if node is None:
            raise ParsingError(errors['name'])

        if intvType not in ['idle', 'atomic', 'conditional', 'stochastic']:
            raise ParsingError("The intervention '" +
                               intvType + "' is not supported.")

        intv = Intervention()
        intv.target = node
        intv.type_ = self.toInterventionType(intvType)

        if intv.type_ == InterventionType.conditional or intv.type_ == InterventionType.stochastic:
            if len(groups) > 2:
                inputParentsText = groups[2]
                names = list(filter(lambda n: n is not None and n !=
                             '', inputParentsText.split(',')))
                nodes = gu.getNodesByName(names, graph)

                if len(names) != len(nodes):
                    raise ParsingError(errors['name'])

                intv.inputParents = nodes

        return intv

    def toInterventionType(self, val):
        if val == 'idle':
            return InterventionType.idle
        elif val == 'atomic':
            return InterventionType.atomic
        elif val == 'conditional':
            return InterventionType.conditional
        elif val == 'stochastic':
            return InterventionType.stochastic
