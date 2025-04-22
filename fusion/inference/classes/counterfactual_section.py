import re

# from src.intervention.classes.intervention import Intervention, InterventionType
# from src.intervention.classes.intervention_task import interventionFieldSuffix
from src.transportability.classes.transportability import targetPopulation
# from src.task.classes.task import TaskSetDefinition
from src.editor.classes.section import Section
from src.editor.classes.parsing_error import ParsingError
from src.inference.classes.counterfactual import Counterfactual, Intervention
from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.counterfactual_utils import CounterfactualUtils


# Regex for parsing counterfactual
#          node name           interventions                   value
#  /^       ([^\s]+)     \s*   (?:\[(.*)\])?  \s*  =  \s*   ([-+]?(?:[0-9]*\.[0-9]+|[0-9]+))
regexExp = r'^([^\s,\[]+)\s*(?:\[(.*)\])?\s*=\s*([-+]?(?:[0-9]*\.[0-9]+|[0-9]+))'

#          node name                                value
#  /^       ([^\s]+)     \s*  =  \s*   ([-+]?(?:[0-9]*\.[0-9]+|[0-9]+))
nodeExp = r'^([^\s,\[]+)\s*=\s*([-+]?(?:[0-9]*\.[0-9]+|[0-9]+))'

#          node name                   node name         [interventions]
#  /^       ([^\s]+)     \s*  =  \s*   ([^\s,\[]+)\s*(?:\[(.*)\])?
intvCtfExp = r'^([^\s,\[]+)\s*=\s*([^\s,\[]+)\s*(?:\[(.*)\])?'

errors = {
    'parse': 'Please specify counterfactuals in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the query\'s section.',
    'name': 'Please specify the name of the node.'
}


class CounterfactualSection(Section):

    tag = '<COUNTERFACTUALS>'
    required = False
    order = 7

    def __init__(self, optTypeMap={}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)
        self.reNode = re.compile(nodeExp)
        self.reIntvCtf = re.compile(intvCtfExp)

    def parse(self, lines, parsedData={}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        graph = parsedData['graph']
        # populations = graph.metadata['populations'] if 'populations' in graph.metadata else [
        #     targetPopulation]

        Ystar = []
        lineNumber = 0

        try:
            for line in lines:
                Yx = self.counterfactualFromString(line, graph)

                Ystar.append(Yx)

                lineNumber = lineNumber + 1

            parsedData['counterfactuals'] = Ystar

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

    def getLines(self):
        return []

    def destroy(self):
        pass

    def counterfactualFromString(self, line, graph):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()

        nodeName = groups[0]
        node = gu.getNodeByName(nodeName, graph)

        if node is None:
            raise ParsingError(errors['name'])

        value = None
        intvs = []

        if len(groups) == 2:
            value = self.parseNumber(groups[1])
        elif len(groups) == 3:
            value = self.parseNumber(groups[2])
            intvsText = groups[1]

            if intvsText is not None:
                intvsTokens = [l.strip() for l in intvsText.split(',')]

                for token in intvsTokens:
                    match = self.reNode.match(token)

                    # X = 0
                    if match is not None:
                        subGroups = match.groups()

                        intvNode = gu.getNodeByName(subGroups[0], graph)

                        if intvNode is None:
                            raise ParsingError(errors['name'])

                        intvValue = self.parseNumber(subGroups[1])

                        X = Intervention(intvNode, intvValue)

                        intvs.append(X)
                    else:
                        match = self.reIntvCtf.match(token)

                        # Z = Z [X = 1, W = 1]
                        if match is not None:
                            subGroups = match.groups()

                            intvNode = gu.getNodeByName(subGroups[0], graph)

                            if intvNode is None:
                                raise ParsingError(errors['name'])

                            ctfIntvText = subGroups[2]

                            match = self.reNode.match(ctfIntvText)

                            if match is not None:
                                groups = match.groups()

                                ctfNode = gu.getNodeByName(groups[0], graph)

                                if ctfNode is None:
                                    raise ParsingError(errors['name'])

                                intvValue = self.parseNumber(groups[1])

                                X = Intervention(
                                    intvNode, Counterfactual(intvNode, None, [Intervention(ctfNode, intvValue)]))

                                intvs.append(X)

        Yx = Counterfactual(node, value, intvs)

        return Yx

    def parseNumber(self, value):
        if '.' in value:
            return float(value)
        else:
            return int(value)
