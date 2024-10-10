from src.adjustment.backdoor_adjustment import BackdoorAdjustment as BD

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.common.object_utils import ObjectUtils as ou


BackdoorAdjustmentName = 'Back-Door adjustment'

class BackdoorAdjustment():

    # /**
    #  * Finds an adjustment expression for the effect P(y | do(x)) according to the given
    #  * parameters if one exists
    #  * @param G The graph
    #  * @param x Treatment variable
    #  * @param y Outcome variable
    #  * @param P Probability expression
    #  * @returns An adjustment expression for P(y | do(x)) or null if none exists
    #  */
    @staticmethod
    def findAdjustment(G, x, y, w, P):
        w = ou.makeArray(w)

        sets = BD.listAdmissibleSets(G, x, y, w, 1)

        # convert node names to nodes
        admNodes = []

        if sets is not None:
            for adm in sets:
                nodes = gu.getNodesByName(adm, G)
                admNodes.append(nodes)

        if len(admNodes) > 0:
            # admissible set
            z = None
            # nodes appearing in P(y | x,s)
            s = None

            for nodes in admNodes:
                # handle the case where an emptyset is null
                if nodes is None:
                    nodes = []

                if len(w) == 0:
                    z = nodes
                    s = nodes
                    break
                else:
                    if su.isSubset(w, nodes, 'name'):
                        s = nodes
                        z = su.difference(s, w, 'name')
                        break
                    else:
                        s = su.union(w, nodes, 'name')
                        z = nodes
                        break

            if s is not None:
                s = sorted(s, key = lambda n: n['name'])

            if z is not None:
                z = sorted(z, key = lambda n: n['name'])

            # if no new covariates are introduced no summation is necessary
            expression = None
            firstTerm = pu.conditional(P, gu.nodesToVariables(y), gu.nodesToVariables(su.union(x, s, 'name')))

            if su.isEmpty(z):
                expression = firstTerm
            else:
                expression = pu.sumOver(eu.create('product', [
                    firstTerm,
                    pu.conditional(P, gu.nodesToVariables(z), [])
                ]), z)

            return {
                'name': BackdoorAdjustmentName,
                'covariates': z,
                'expression': expression
            }
        else:
            return None