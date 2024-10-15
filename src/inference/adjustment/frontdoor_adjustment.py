from src.path_analysis.d_separation import DSeparation

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu
from src.common.object_utils import ObjectUtils as ou


FrontDoorAdjustmentName = 'Front-Door adjustment'


class FrontdoorAdjustment():

    # /**
    # * Finds a front-door adjustment expression for the effect P(y | do(x)) according to the given
    # * parameters if one exists
    # * @param G The graph
    # * @param x Treatment variable
    # * @param y Outcome variable
    # * @param P Probability expression
    # * @returns An adjustment expression for P(y | do(x)) or null if none exists
    # */

    @staticmethod
    def findAdjustment(G, x, y, P):
        z = su.difference(su.intersection(gu.ancestors(y, G), gu.descendants(
            x, G), 'name'), su.union(x, y, 'name'), 'name')

        Gxy = gu.transform(G, x, [])
        Gxz = gu.transform(G, [], x)
        Gzy = gu.transform(G, [], z)

        if DSeparation.test(Gxy, x, y, z) and DSeparation.test(Gxz, x, z, []) and DSeparation.test(Gzy, z, y, x):
            # do we need to reduce separator?
            # z = Adjustment.reduceSeparator(Gxy, x, y, z);

            if (su.isEmpty(z)):
                return {
                    'name': FrontDoorAdjustmentName,
                    'covariates': [],
                    'expression': pu.conditional(P, gu.nodesToVariables(y), [])
                }
            else:
                return {
                    'name': FrontDoorAdjustmentName,
                    'covariates': z,
                    'expression': pu.sumOver(eu.create("product", [
                        pu.conditional(P, gu.nodesToVariables(
                            z), gu.nodesToVariables(x)),
                        pu.sumOver(eu.create("product", [
                            pu.conditional(P, gu.nodesToVariables(
                                y), gu.nodesToVariables(su.union(x, z))),
                            pu.conditional(P, gu.nodesToVariables(x), [])
                        ]), x)
                    ]), gu.nodesToVariables(z))
                }
        else:
            return None
