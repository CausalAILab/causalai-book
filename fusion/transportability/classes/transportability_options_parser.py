from src.editor.classes.options_parser import OptionsParser
from src.transportability.classes.transportability import transportabilityNodeType


class TransportabilityOptionsParser(OptionsParser):

    def getType(self):
        return transportabilityNodeType


    def toString(self, target, graph):
        return ''


    def fromString(self, line, target, graph):
        if not graph or 'populations' not in graph.metadata:
            return

        populations = graph.metadata['populations']
        popLabels = []
        labels = list(map(lambda s: s.strip(), line.split(','))) if line else []
        
        for label in labels:
            if label == '':
                continue

            found = False

            for pop in populations:
                if pop.label == label:
                    found = True
                    popLabels.append(pop.label)
                    break

            if not found:
                raise Exception('Please specify valid population label(s).')

        if 'metadata' not in target:
            target['metadata'] = {}
        
        target['metadata']['populations'] = popLabels