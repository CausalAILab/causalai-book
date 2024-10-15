import re
from typing import Dict

from src.graph.classes.graph import Graph
from src.graph.classes.graph_defs import edgeTypeMap, directedEdgeType, bidirectedEdgeType
from src.editor.classes.section import Section
from src.editor.classes.options_parser import OptionsParser
from src.editor.classes.parsing_error import ParsingError


# Regex for parsing node strings
#       from           type            to                 options                   curvature
#  /^ ([^\s]+)  \s+  ([^\s]+)  \s+   ([^\s]+)   (?:\s+\[  (.*)  \])?  (?:\s+((?:\+|-)?(?:0(?:\.\d+)?|1)))?  \s*  $/
regexExp = r'^([^\s]+)\s+([^\s]+)\s+([^\s]+)(?:\s+\[(.*)\])?(?:\s+((?:\+|-)?(?:\d+(?:\.\d+)?|\d+)))?\s*$'

errors = {
    'parse': 'Please specify an edge in correct format.',
    'nodesTagMissing': 'Please specify the nodes before edges.',
    'sourceNodeMissing': 'Please specify a valid source node.',
    'destinationNodeMissing': 'Please specify a valid destination node.',
    'edgeTypeMissing': 'Please specify a valid edge type.'
}

class EdgesSection(Section):

    tag = '<EDGES>'
    required = True
    order = 3
    optTypeMap = Dict[str, OptionsParser]
    semiMarkovianMode = True

    def __init__(self, optTypeMap = {}):
        self.optTypeMap = optTypeMap
        self.re = re.compile(regexExp)
        self.nodeMap = {}


    def parse(self, lines, parsedData = {}):
        if 'graph' not in parsedData:
            return ParsingError(errors['nodesTagMissing'])

        graph = parsedData['graph']

        self.nodeMap = {}

        for node in graph.nodes:
            self.nodeMap[node['name']] = node

        lineNumber = 0

        try:
            for line in lines:
                edge = self.edgeFromString(line, graph)

                filterEdge = list(filter(lambda e: e['from_'] == edge['from_'] and e['to_'] == edge['to_'] and e['type_'] == edge['type_'], graph.edges))
                # filterEdge = list(filter(lambda e: e['from_'] == edge['from_'] and e['to_'] == edge['to_'], graph.edges))
                
                if len(filterEdge) > 0:
                    edgeType = self.getEdgeType(edge['type_'])
                    shortId = edgeType.shortId if edgeType is not None else directedEdgeType.shortId

                    return ParsingError('The edge ' + edge['from_'] + ' ' + shortId + ' ' + edge['to_'] + ' already exists.', lineNumber)

                if edge['type_'] == bidirectedEdgeType.id_:
                    if self.semiMarkovianMode:
                        graph.addEdges(edge)
                    else:
                        continue
                else:
                    graph.addEdges(edge)

                # check for cycle

                lineNumber = lineNumber + 1

            return parsedData
        except ParsingError as e:
            return ParsingError(e.message, lineNumber)

        return parsedData

    
    #     try {
    #         for (let line of lines) {
    #             let edge: Edge = this.edgeFromString(line, graph);

    #             if (edge.type == bidirectedEdgeType.id) {
    #                 if (this.semiMarkovianMode)
    #                     graph.edges.push(edge);
    #                 else {
    #                     let nodeInfo = ProjectionUtils.bidirectedEdgeToLatentNode(edge, graph, false);

    #                     // check for duplicate node
    #                     let filterNames = graph.nodes.filter(n => n.name == nodeInfo.node.name);

    #                     if (filterNames.length > 0)
    #                         return new ParsingError(lineNumber, 'The node ' + nodeInfo.node.name + ' already exists.');

    #                     let filterLabels = graph.nodes.filter(n => n.label == nodeInfo.node.label);

    #                     if (filterLabels.length > 0)
    #                         return new ParsingError(lineNumber, 'The node ' + nodeInfo.node.name + ' already exists.');

    #                     // check for duplicate edge
    #                     let filterEdgeFrom = graph.edges.filter(e => e.from == nodeInfo.fromEdge.from && e.to == nodeInfo.fromEdge.to && e.type == nodeInfo.fromEdge.type);

    #                     if (filterEdgeFrom.length > 0) {
    #                         let shortId: string = this.getEdgeType(nodeInfo.fromEdge.type) ? this.getEdgeType(nodeInfo.fromEdge.type).shortId : directedEdgeType.shortId;

    #                         return new ParsingError(lineNumber, 'The edge ' + nodeInfo.fromEdge.from + ' ' + shortId + ' ' + nodeInfo.fromEdge.to + ' already exists.');
    #                     }

    #                     let filterEdgeTo = graph.edges.filter(e => e.from == nodeInfo.toEdge.from && e.to == nodeInfo.toEdge.to && e.type == nodeInfo.toEdge.type);

    #                     if (filterEdgeTo.length > 0) {
    #                         let shortId: string = this.getEdgeType(nodeInfo.toEdge.type) ? this.getEdgeType(nodeInfo.toEdge.type).shortId : directedEdgeType.shortId;

    #                         return new ParsingError(lineNumber, 'The edge ' + nodeInfo.toEdge.from + ' ' + shortId + ' ' + nodeInfo.toEdge.to + ' already exists.');
    #                     }

    #                     graph.nodes.push(nodeInfo.node);
    #                     graph.edges.push(nodeInfo.fromEdge);
    #                     graph.edges.push(nodeInfo.toEdge);
    #                 }
    #             } else
    #                 graph.edges.push(edge);

    #             if (GraphUtils.hasCycles(graph)) {
    #                 let shortId: string = this.getEdgeType(edge.type) ? this.getEdgeType(edge.type).shortId : directedEdgeType.shortId;

    #                 return new ParsingError(lineNumber, 'The edge ' + edge.from + ' ' + shortId + ' ' + edge.to + ' creates a cycle.', [edge]);
    #             }

    #             lineNumber++;
    #         }
    #         return parsedData;
    #     } catch (e) {
    #         return new ParsingError(lineNumber, e.message);
    #     }
    # }


    # str, Graph
    # Edge
    def edgeFromString(self, line, graph):
        match = self.re.match(line)

        if match is None:
            raise ParsingError(errors['parse'])

        # from, etype, to, options, curvature
        groups = match.groups()
        
        fromText = groups[0]
        eType = groups[1]
        toText = groups[2]
        options = groups[3]

        if fromText is None:
            raise ParsingError(errors['sourceNodeMissing'])

        fromNode = self.nodeMap[fromText] if fromText in self.nodeMap else None

        if fromNode is None:
            raise ParsingError('The node ' + fromText + ' does not exist.')

        if toText is None:
            raise ParsingError(errors['destinationNodeMissing'])

        toNode = self.nodeMap[toText] if toText in self.nodeMap else None

        if toNode is None:
            raise ParsingError('The node ' + toText + ' does not exist.')

        if eType is None:
            raise ParsingError(errors['edgeTypeMissing'])

        edgeType = self.getEdgeType(eType)

        if edgeType is None:
            raise ParsingError("The edge type '" + eType + "' is not supported.")

        parser = None

        if edgeType.id_ not in self.optTypeMap:
            if directedEdgeType.id_ in self.optTypeMap:
                parser = self.optTypeMap[directedEdgeType.id_]
        else:
            parser = self.optTypeMap[edgeType.id_]

        edge = {'from_': fromNode['name'], 'to_': toNode['name'], 'type_': edgeType.id_, 'metadata': {}}

        if parser is not None:
            parser.fromString(options, edge, graph)

        return edge


    # str
    # EdgeType
    def getEdgeType(self, shortId):
        if shortId is None:
            return None
        
        for id_ in edgeTypeMap:
            if shortId.upper() == edgeTypeMap[id_].shortId.upper():
                return edgeTypeMap[id_]

        return None


    def getLines(self):
        return []


    def destroy(self):
        pass