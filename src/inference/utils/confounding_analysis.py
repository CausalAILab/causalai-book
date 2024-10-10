from src.inference.utils.probability_utils import ProbabilityUtils as pu
from src.inference.utils.expression_utils import ExpressionUtils as eu


class ConfoundingAnalysis():

    # /**
    #  * Tian's Lemma 11 (ii). Computes Q[Hi] from Q[H] where Hi is a c-component of G(H).
    #  * @param Hi The c-component to compute Q[Hi]
    #  * @param H A set of nodes, assumed to be in topological order according to G(H)
    #  * @param QH Expression for Q[H]
    #  * @returns Expression for Q[Hi]
    #  */
    @staticmethod
    def qComputeCComp(Hi, H, QH):
        result = None

        if QH.type_ == 'prob':
            factors = []

            for i in range(len(H)):
                if H[i] in Hi:
                    factors.append(pu.conditional(QH, H[i], H[0:i], H))

            factors.reverse()

            result = eu.create('product', factors)
        else:
            # num = [None] * len(Hi)
            # den = [None] * len(Hi)
            num = [None] * len(H)
            den = [None] * len(H)

            # determine which factors Q[H^(i)] belong to the denominator and numerator
            for i in range(len(H)):
                if H[i] in Hi:
                    num[i] = 1

                    if i >= 1:
                        den[i - 1] = 1

            fNum = []
            fDen = []

            # cancel Q[H^(i)] factors that appear in both
            for i in range(len(H)):
                if num[i] == 1 and den[i] == 1:
                    num[i] = 0
                    den[i] = 0

                if num[i]:
                    fNum.append(pu.sumOver(QH, H[i+1:]))

                if den[i]:
                    fDen.append(pu.sumOver(QH, H[i+1:]))

            if len(fDen) > 0:
                result = eu.create(
                    'frac', [eu.create('product', fNum), eu.create('product', fDen)])
            else:
                result = eu.create('product', fNum)

        # return pu.simplify(result)
        return result
