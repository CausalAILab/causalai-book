# import re
from typing import Dict

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import basicNodeType, nodeTypeMap
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError
from src.inference.utils.graph_utils import GraphUtils as gu


# Regex for parsing node strings
#       name          label             type                 options                coordinates
#  /^  ([^\s]+) (?:\s+ "(.*)" )?  (?:\s+ (\w+) )?   (?:\s+\[    (.*)  \])?   (?:\s+([-+]?[0-9]*\.?[0-9]+),\s*([-+]?[0-9]*\.?[0-9]+))?  $/
# regexExp = r'^([^\s]+)$'

errors = {
    # 'parse': 'Please specify name(s) in correct format.'
    'name': 'Please specify the name of the node.'
}

class ExternalDataSection(Section):

    tag = '<EXTERNAL_DATA>'
    required = False
    order = 7
    optTypeMap = Dict[str, OptionsParser]

    def __init__(self, optTypeMap = {}):
        self.optTypeMap = optTypeMap
        # self.re = re.compile(regexExp)


    def parse(self, lines, parsedData = {}):
        if 'graph' not in parsedData:
            parsedData['graph'] = Graph()

        graph = parsedData['graph']
        externalData = []

        lineNumber = 0
        
        try:
            for line in lines:
                nodeNames = self.nodesFromString(line, graph)
                externalData = externalData + nodeNames

                lineNumber = lineNumber + 1

            parsedData['external'] = externalData

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)


    def getLines(self):
        return []


    def destroy(self):
        pass

    
    def nodesFromString(self, line, graph):
        names = list(filter(lambda n: n is not None and n != '', line.split(',')))
        nodes = gu.getNodesByName(names, graph)

        if len(names) != len(nodes):
            raise ParsingError(errors['name'])

        names = list(map(lambda n: n['name'], nodes))

        return names