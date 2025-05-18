import re
from typing import Dict

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import basicNodeType
from src.graph_analysis.sigma_calculus.classes.sigma_calculus_inspection_query import SigmaCalculusInspectionQuery
from src.graph_analysis.classes.probability_expression import ProbabilityExpression
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing query
#       definition                 list
#  /^   ([^\s]+)   \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

errors = {
    'parse': 'Please specify a query in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the query\'s section.',
    'rule': 'Please specify a valid rule (1, 2, or 3).',
    'name': 'Please specify the name of the node.'
}

class QuerySection(Section):

    tag = '<QUERY>'
    required = False
    order = 4

    def __init__(self, optTypeMap = {}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)


    def parse(self, lines, parsedData = {}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        graph = parsedData['graph']
        P = ProbabilityExpression()
        query = SigmaCalculusInspectionQuery()

        lineNumber = 0

        try:
            for line in lines:
                taskSet = self.setFromString(line, graph)
                df = taskSet['def']
                content = taskSet['content']

                if df == 'rule':
                    query.rule = content
                elif df == 'treatment':
                    P.Z = content
                elif df == 'outcome':
                    P.Y = content
                elif df == 'conditional':
                    P.W = content
                elif df == 'interventional':
                    P.X = content

                lineNumber = lineNumber + 1
            
            query.P = P

            parsedData['query'] = query

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

        return parsedData


    def getLines(self):
        return []


    def destroy(self):
        pass

    
    def setFromString(self, line, graph):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()
        
        defText = groups[0]
        listText = groups[1]

        definition = self.getTaskDefinition(defText)

        if definition is None:
            raise ParsingError("The task '" + defText + "' is not supported.")

        if defText == 'rule':
            ruleNum = int(listText)

            if ruleNum not in [1,2,3]:
                raise ParsingError(errors['rule'])

            content = ruleNum
        else:
            # parse variables
            names = list(filter(lambda n: n is not None and n != '', listText.split(',')))
            nodes = list(filter(lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(names, graph)))
            
            if len(names) != len(nodes):
                raise ParsingError(errors['name'])

            content = nodes

        return {'def': defText, 'content': content}


    def getTaskDefinition(self, name):
        filterDef = list(filter(lambda n: n == name, ['rule', 'treatment', 'outcome', 'conditional', 'interventional']))

        if len(filterDef) > 0:
            return filterDef[0]
        else:
            return None