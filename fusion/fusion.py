from src.inference.utils.graph_utils import GraphUtils as gu

from src.editor.input_parser import InputParser
from src.editor.sections.nodes_section import NodesSection
from src.editor.sections.edges_section import EdgesSection
from src.editor.sections.task_section import TaskSection
from src.editor.sections.populations_section import PopulationsSection
from src.editor.sections.experiments_section import ExperimentsSection


from src.graph.classes.graph_defs import latentNodeType, bidirectedEdgeType
from src.cluster.classes.cluster import clusterNodeType
from src.selection_bias.classes.selection_bias import selectionBiasNodeType
from src.transportability.classes.transportability import targetPopulation, transportabilityNodeType
from src.intervention.classes.intervention import interventionNodeType


from src.cluster.classes.cluster_options_parser import ClusterOptionsParser
from src.selection_bias.classes.selection_bias_options_parser import SelectionBiasOptionsParser
from src.transportability.classes.transportability_options_parser import TransportabilityOptionsParser
from src.intervention.classes.intervention_options_parser import InterventionOptionsParser
from src.editor.classes.latent_options_parser import LatentOptionsParser
from src.editor.classes.bidirected_options_parser import BidirectedOptionsParser


from src.task.basic_task import treatmentDefName, outcomeDefName, adjustedDefName

def getNodesSection():
    nodeTypeParsers = {}
    nodeTypeParsers[latentNodeType.id_] = LatentOptionsParser()
    nodeTypeParsers[clusterNodeType.id_] = ClusterOptionsParser()
    nodeTypeParsers[selectionBiasNodeType.id_] = SelectionBiasOptionsParser()
    nodeTypeParsers[transportabilityNodeType.id_] = TransportabilityOptionsParser()
    nodeTypeParsers[interventionNodeType.id_] = InterventionOptionsParser()

    return NodesSection(nodeTypeParsers)


def getEdgesSection():
    edgeTypeParsers = {}
    edgeTypeParsers[bidirectedEdgeType.id_] = BidirectedOptionsParser()
    return EdgesSection(edgeTypeParsers)


def listDSeparationPaths(fileContent):

    parser = InputParser()
    parser.sections = [getNodesSection(), getEdgesSection(),
                       TaskSection(), PopulationsSection(), ExperimentsSection()]
    parsedData = parser.parse(fileContent)

    G = parsedData['graph']
    T = parsedData['task']

    X = gu.getNodesByName(T.sets[treatmentDefName], G)
    Y = gu.getNodesByName(T.sets[outcomeDefName], G)
    Z = gu.getNodesByName(T.sets[adjustedDefName], G)

    from src.path_analysis.d_separation import DSeparation

    connectedPaths = DSeparation.findDConnectedPaths(G, X, Y, Z)
    separatedPaths = DSeparation.findDSeparatedPaths(G, X, Y, Z)

    return {'G':G, 'connectedPaths': connectedPaths, 'separatedPaths': separatedPaths}


def parseGraph(fileContent):
    parser = InputParser()
    parser.sections = [getNodesSection(), getEdgesSection()]
    parsedData = parser.parse(fileContent)
    return parsedData['graph']