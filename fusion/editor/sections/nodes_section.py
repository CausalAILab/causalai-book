import re
from typing import Dict

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import basicNodeType, nodeTypeMap
from src.selection_bias.classes.selection_bias import selectionBiasNodeType
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError


# Regex for parsing node strings
#       name          label             type                 options                coordinates
#  /^  ([^\s]+) (?:\s+ "(.*)" )?  (?:\s+ (\w+) )?   (?:\s+\[    (.*)  \])?   (?:\s+([-+]?[0-9]*\.?[0-9]+),\s*([-+]?[0-9]*\.?[0-9]+))?  $/
regexExp = r'^([^\s]+)(?:\s+"(.*)")?(?:\s+(\w+))?(?:\s+\[(.*)\])?(?:\s+([-+]?[0-9]*\.?[0-9]+),\s*([-+]?[0-9]*\.?[0-9]+))?$'

errors = {
    'parse': 'Please specify a node in correct format.',
    'name': 'Please specify the name of the node.'
}

class NodesSection(Section):

    tag = '<NODES>'
    required = True
    order = 2
    optTypeMap = Dict[str, OptionsParser]

    def __init__(self, optTypeMap = {}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)


    def parse(self, lines, parsedData = {}):
        if parsedData is None:
            parsedData = {}
        
        if 'graph' not in parsedData:
            parsedData['graph'] = Graph()

        graph = parsedData['graph']

        lineNumber = 0
        numSBNodes = 0
        
        try:
            for line in lines:
                node = self.nodeFromString(line, graph)

                filterByName = list(filter(lambda n: n['name'] == node['name'], graph.nodes))

                if len(filterByName) > 0:
                    return ParsingError('The node ' + node['name'] + ' already exists.', lineNumber)

                filterByLabel = list(filter(lambda n: n['label'] == node['label'], graph.nodes))

                if len(filterByLabel) > 0:
                    return ParsingError('The node ' + node['name'] + ' already exists.', lineNumber)

                if node['type_'] == selectionBiasNodeType.id_:
                    numSBNodes = numSBNodes + 1

                if numSBNodes > 1:
                    return ParsingError('Please specify one selection bias node.', lineNumber)

                graph.addNodes(node)

                lineNumber = lineNumber + 1

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)


    def getLines(self):
        return []


    def destroy(self):
        pass

    
    def nodeFromString(self, line, graph):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        # name, label, type, options, x, y
        groups = match.groups()
        
        name = groups[0]
        label = groups[1]
        ntype = groups[2]
        options = groups[3]

        if name is None:
            raise ParsingError(errors['name'])

        if label is None or label == '':
            label = name

        nodeType = self.getNodeType(ntype)

        if nodeType is None:
            nodeType = basicNodeType

        parser = None

        if nodeType.id_ not in self.optTypeMap:
            if basicNodeType.id_ in self.optTypeMap:
                parser = self.optTypeMap[basicNodeType.id_]
        else:
            parser = self.optTypeMap[nodeType.id_]

        node = {'name': name, 'label': label, 'type_': nodeType.id_, 'metadata': {}}

    #     if (nodeType.id == latentNodeType.id)
    #         node.metadata.distributionInfo = { data_type: 'discrete', metadata: { probabilityInfo: { 0: 0.5, 1: 0.5 } } };

        if parser is not None:
            parser.fromString(options, node, graph)

        return node


    def getNodeType(self, shortId):
        if shortId is None:
            return None

        for id_ in nodeTypeMap:
            if shortId.upper() == id_.upper():
                return nodeTypeMap[id_]

        return None