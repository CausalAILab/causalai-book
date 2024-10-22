import re
from typing import Dict

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import basicNodeType
from src.graph_analysis.classes.transform_nodes import TransformNodes
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing transformation
#       definition                 list
#  /^   ([^\s]+)   \s*   :   \s*  (.*) $/
regexExp = r'^([^\s]+)\s*:\s*(.*)$'

errors = {
    'parse': 'Please specify a transformation in correct format.',
    'graphTagMissing': 'Please specify the nodes and edges before the transformation\'s section.',
    'name': 'Please specify the name of the node.'
}

class TransformationSection(Section):

    tag = '<TRANSFORMATION>'
    required = False
    order = 5

    def __init__(self, optTypeMap = {}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)


    def parse(self, lines, parsedData = {}):
        if 'graph' not in parsedData:
            return ParsingError(errors['graphTagMissing'])

        graph = parsedData['graph']
        tx = TransformNodes()

        lineNumber = 0

        try:
            for line in lines:
                txSet = self.transformationFromString(line, graph)
                df = txSet['def']
                nodes = txSet['nodes']

                if df == 'over':
                    tx.over = nodes
                elif df == 'under':
                    tx.under = nodes

                lineNumber = lineNumber + 1
            
            parsedData['transformation'] = tx

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

        return parsedData


    def getLines(self):
        return []


    def destroy(self):
        pass

    
    def transformationFromString(self, line, graph):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        groups = match.groups()
        
        defText = groups[0]
        listText = groups[1]

        definition = self.getDefinition(defText)

        if definition is None:
            raise ParsingError("The task '" + defText + "' is not supported.")

        # parse variables
        names = list(filter(lambda n: n is not None and n != '', listText.split(',')))
        nodes = list(filter(lambda n: n['type_'] == basicNodeType.id_, gu.getNodesByName(names, graph)))

        if len(names) != len(nodes):
            raise ParsingError(errors['name'])

        return {'def': definition, 'nodes': nodes}


    def getDefinition(self, name):
        filterDef = list(filter(lambda n: n == name, ['over', 'under']))

        if len(filterDef) > 0:
            return filterDef[0]
        else:
            return None