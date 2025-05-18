from src.editor.classes.options_parser import OptionsParser
from src.cluster.classes.cluster import clusterNodeType


class ClusterOptionsParser(OptionsParser):

    def getType(self):
        return clusterNodeType


    def toString(self, target, graph):
        return ''


    def fromString(self, text, target, graph):
        pass


    # toString(target: INode, graph: Graph): string {
    #     let numVar = target.metadata.numVariables;

    #     if (!numVar) return '';

    #     return '' + numVar;
    # }

    # fromString(str: string, target: INode, graph: Graph): void {
    #     let num = parseInt(str);

    #     if (isNaN(num)
    #         || (!isNaN(num) && num < 2 || num > 100))
    #         throw new Error(errors.numVariables);

    #     // target.label = this.getClusterLabel(target.name, num, target.metadata.subscript);
    #     target.label = this.getClusterLabel(target.name, num);
    #     target.metadata.numVariables = num;
    # }

    # // private getClusterLabel(baseName: string, numVariables: number, subscript?: string) {
    # private getClusterLabel(baseName: string, numVariables: number) {
    #     return numVariables <= 1 || numVariables > 100 ? baseName : baseName + '^{[1,' + numVariables + ']}';
    # }