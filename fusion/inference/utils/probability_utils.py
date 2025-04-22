from src.inference.classes.expression import Expression

from src.inference.utils.set_utils import SetUtils as su
from src.common.object_utils import ObjectUtils as ou
from src.inference.utils.expression_utils import ExpressionUtils as eu


class ProbabilityUtils():

    #     /**
    #      *
    #      * P_{P.do} (a | b + P.given)
    #      * P_{P[2]} (a | b + P[1])
    #      * @param P
    #      * @param a
    #      * @param b
    #      * @param context
    #      */
    @staticmethod
    def conditional(P, a, b, context=None):
        a = ou.makeArray(a)
        b = ou.makeArray(b)

        if context is None:
            context = ProbabilityUtils.listVariables(P)

        context = ou.makeArray(context)

        if P is not None and P.type_ == 'prob':
            if len(P.parts) >= 2:
                parts = [a]

                cond = P.parts[1]
                cond = ou.makeArray(cond)
                parts.append(su.union(b, cond, 'name'))

                if len(P.parts) >= 3:
                    parts.append(P.parts[2])

                if len(P.parts) >= 4:
                    parts.append(P.parts[3])

                if len(P.parts) >= 5:
                    parts.append(P.parts[4])

                return eu.create('prob', parts)
            else:
                return eu.create('prob', [a, b])

        return eu.create('frac', [
            # numerator
            # sum over all variables that are not in "a" or "b" in the context of the expression
            ProbabilityUtils.sumOver(
                ou.clone(P), su.difference(context, a + b, 'name')),
            # denominator
            # sum over all variables that are not in "b" in the context
            ProbabilityUtils.sumOver(
                ou.clone(P), su.difference(context, b, 'name'))
        ])

    # Expression, Variable | Variable[]
    # Expression

    @staticmethod
    def sumOver(P, a):
        if not P:
            return None

        a = ou.makeArray(a)

        result = None

        if P.type_ == 'prob':
            return eu.create('prob', [
                su.difference(P.parts[0], a, 'name'),
                P.parts[1] if len(P.parts) > 1 else None,
                P.parts[2] if len(P.parts) > 2 else None,
                P.parts[3] if len(P.parts) > 3 else None
            ])
        elif P.type_ == 'sum':
            result = eu.create('sum', [
                su.union(P.parts[0], a, 'name'),
                P.parts[1] if len(P.parts) > 1 else None,
                P.parts[2] if len(P.parts) > 2 else None
            ])
        else:
            result = eu.create('sum', [a, None, P])

        if result is not None:
            return ProbabilityUtils.simplify(result)

        return result

    @staticmethod
    def listVariables(P, cond=False):
        if eu.isEmpty(P):
            return []

        if isinstance(P, list):
            variables = []

            for part in P:
                if not isinstance(part, str):
                    variables = su.union(
                        variables, ProbabilityUtils.listVariables(part, cond), 'name')

            return variables

        if not isinstance(P, Expression):
            if 'name' in P:
                return [P]
        else:
            if P.type_ == 'product':
                return ProbabilityUtils.listVariables(P.parts, cond)

            elif P.type_ == 'sum':
                return ProbabilityUtils.listVariables(P.parts[2], cond)

            elif P.type_ == 'prob':
                if cond:
                    if len(P.parts) >= 3:
                        return ProbabilityUtils.listVariables(su.union(P.parts[1], P.parts[2], 'name'))
                    elif len(P.parts) >= 2:
                        return ProbabilityUtils.listVariables(P.parts[1])
                    else:
                        return ProbabilityUtils.listVariables(P.parts[0])
                else:
                    return ProbabilityUtils.listVariables(P.parts[0])

            else:
                return []

        return []

    @staticmethod
    def simplify(e):
        if e is None or not isinstance(e, Expression):
            return e

        for i in range(len(e.parts)):
            e.parts[i] = ProbabilityUtils.simplify(e.parts[i])

        if e.type_ == 'sum':
            return ProbabilityUtils.simplifySum(e)
        elif e.type_ == 'frac':
            return ProbabilityUtils.simplifyFraction(e)
        elif e.type_ == 'product':
            return ProbabilityUtils.simplifyProduct(e)
        elif e.type_ == 'prob':
            return ProbabilityUtils.simplifyProb(e)

        return e

    @staticmethod
    def simplifySum(e):
        if eu.isEmpty(e.parts[0]):
            return e.parts[2]

        # sum of a sum
        elif len(e.parts) >= 3 and e.parts[2] is not None and e.parts[2].type_ == 'sum':
            innerSum = e.parts[2]

            return eu.create('sum', [su.union(e.parts[0], innerSum.parts[0], 'name'), None, innerSum.parts[2]])

        # sum of a probability expression
        elif len(e.parts) >= 3 and e.parts[2] is not None and e.parts[2].type_ == 'prob':
            probExp = e.parts[2]
            varsInSum = e.parts[0]
            varsInP = probExp.parts[0]
            sumout = su.intersection(varsInSum, varsInP, 'name')
            e.parts[0] = su.difference(varsInSum, sumout, 'name')
            probExp.parts[0] = su.difference(varsInP, sumout, 'name')

            if len(e.parts[0]) == 0:
                exp = eu.create('prob', [probExp.parts[0]])

                if len(probExp.parts) >= 2:
                    exp.parts.append(probExp.parts[1])
                if len(probExp.parts) >= 3:
                    exp.parts.append(probExp.parts[2])
                if len(probExp.parts) >= 4:
                    exp.parts.append(probExp.parts[3])

                return exp

        # sum of a product of probability factors
        elif len(e.parts) >= 3 and e.parts[2] is not None and e.parts[2].type_ == 'product':
            prodExp = e.parts[2]
            allProb = True

            for part in prodExp.parts:
                allProb = allProb and isinstance(
                    part, Expression) and part.type_ == 'prob'

            if allProb:
                return ProbabilityUtils.simplifySumProductProb(e)

        return e

    @staticmethod
    def simplifySumProductProb(e):
        e = ou.clone(e)

        product = e.parts[2]
        product.parts = list(
            filter(lambda p: not su.isEmpty(p.parts[0]), product.parts))

        # create a map with all the variables in the sum
        dep = {}

        for part in e.parts[0]:
            dep[part['name']] = 0

        # list all variables in the unconditional and conditional part of the probabilities
        variables = []

        for i in range(len(product.parts)):
            variables.append({
                'a': ProbabilityUtils.listVariables(product.parts[i], False),
                'b': ProbabilityUtils.listVariables(product.parts[i], True),
                'removed': False
            })

        # count the number of times each variable of the sum appears in the conditional part of a expression
        for pi in variables:
            for v in pi['b']:
                if v['name'] in dep:
                    dep[v['name']] = dep[v['name']] + 1

        # if there is a variable in the scope of the sum that

        def canSimplify(d):
            for v in d:
                if d[v] <= 0:
                    return True

            return False

        while canSimplify(dep):
            for i in range(len(product.parts)):
                # skip factors already marked for removal
                if variables[i]['removed']:
                    continue

                # get variables that are not in the sum or appear in other factors
                newScope = list(
                    filter(lambda v: v['name'] not in dep or dep[v['name']] > 0, variables[i]['a']))

                # if there are no more variables left, this factor will disappear then we discount
                # the count of appeareances for the variables in the conditional part of this factor
                if su.isEmpty(newScope):
                    for v in variables[i]['b']:
                        if v['name'] in dep:
                            dep[v['name']] = dep[v['name']] - 1

                    variables[i]['removed'] = True

                # delete the simplified variables from the scope of the sum
                simplified = su.difference(variables[i]['a'], newScope, 'name')

                for v in simplified:
                    del dep[v['name']]

                variables[i]['a'] = newScope

        newFactors = []

        # keep non-removed factors
        for i in range(len(product.parts)):
            factor = ou.clone(product.parts[i])
            factor.parts[0] = su.intersection(
                factor.parts[0], variables[i]['a'], 'name')

            if not variables[i]['removed']:
                newFactors.append(factor)

        # update product
        product.parts = newFactors

        if len(newFactors) == 0:
            return None

        # what happens if all summed out?
        # if product has only one factor get the factor instead
        newSumOperand = product if len(newFactors) > 1 else newFactors[0]
        e.parts[2] = newSumOperand

        # update the sum scope
        newSumScope = list(filter(lambda f: f['name'] in dep, e.parts[0]))
        e.parts[0] = newSumScope

        # if there are no variables in the sum's scope just get the operand
        newExpression = e if len(newSumScope) > 0 else newSumOperand

        return newExpression

    @staticmethod
    def simplifyFraction(frac, trySimpFactors=True):
        if frac.type_ != 'frac':
            return frac

        num = frac.parts[0] = ProbabilityUtils.simplify(frac.parts[0])
        den = frac.parts[1] = ProbabilityUtils.simplify(frac.parts[1])

        if eu.isEmpty(num) and (eu.isEmpty(den) or den == 1):
            return None

        if eu.isEmpty(den) or den == 1:
            return num

        if (num.type_ != 'prob' and num.type_ != 'product') or (den.type_ != 'prob' and den.type_ != 'product'):
            return frac

        if not trySimpFactors:
            return eu.create('frac', [num, den])

        # turn numerator and denominator into products for the next part
        if num.type_ == 'prob':
            num = eu.create('product', [num])

        if den.type_ == 'prob':
            den = eu.create('product', [den])

        newNumParts = []
        remDenParts = []
        simpF = None

        for fNum in num.parts:
            simpF = None
            remDenParts = []

            for fDen in den.parts:
                simpF = ProbabilityUtils.divideFactors(fNum, fDen)

                if simpF is not None:
                    remDenParts.append(fDen)
                    break

            den.parts = su.difference(den.parts, remDenParts)

            if simpF is not None:
                newNumParts.append(simpF)
            else:
                newNumParts.append(fNum)

        return ProbabilityUtils.simplifyFraction(eu.create('frac', [
            ProbabilityUtils.simplify(eu.create('product', newNumParts)),
            ProbabilityUtils.simplify(eu.create('product', den.parts))
        ]), False)

    @staticmethod
    def divideFactors(num, den):
        # if they are not probability expressions, the denominator's factor variables
        # are not a subset of the numerator's factor variables, the conditional part does not
        # match in the factors, the intervention does not match or they have different superscripts
        # we will not simplify. Then return null.
        if not isinstance(num, Expression) or not isinstance(den, Expression):
            return None

        if num.type_ != 'prob' or den.type_ != 'prob':
            return None

        if not su.isSubset(den.parts[0], num.parts[0], 'name'):
            return None

        if len(num.parts) >= 2 and len(den.parts) >= 2 and not su.equals(num.parts[1], den.parts[1], 'name'):
            return None

        if len(num.parts) >= 3 and len(den.parts) >= 3 and not su.equals(num.parts[2], den.parts[2], 'name'):
            return None

        if len(num.parts) >= 4 and len(den.parts) >= 4 and num.parts[3] != den.parts[3]:
            return None

        numParts0 = num.parts[0]
        denParts0 = den.parts[0]
        numParts1 = []

        if len(num.parts) >= 2 and num.parts[1] is not None:
            numParts1 = num.parts[1]

        if isinstance(numParts0, list) and isinstance(denParts0, list) and isinstance(numParts1, list):
            if len(list(filter(lambda e: 'name' in e and e['name'] is not None, denParts0))) > 0:
                if len(list(filter(lambda e: 'name' in e and e['name'] is not None, numParts0))) > 0:
                    exp = eu.create('prob', [su.difference(
                        num.parts[0], den.parts[0], 'name')])

                    if len(num.parts) >= 2:
                        exp.parts.append(
                            su.union(den.parts[0], num.parts[1], 'name'))

                    if len(num.parts) >= 3:
                        exp.parts.append(num.parts[2])

                    if len(num.parts) >= 4:
                        exp.parts.append(num.parts[3])

                    return exp

    @staticmethod
    def simplifyProduct(prod):
        if prod is None or prod.type_ != 'product':
            return prod

        prod.parts = list(filter(lambda p: not eu.isEmpty(p), prod.parts))

        # empty product
        if isinstance(prod.parts, list) and len(prod.parts) == 0:
            return None

        # product with a single factor
        if isinstance(prod.parts, list) and len(prod.parts) == 1:
            return prod.parts[0]

        return prod

    @staticmethod
    def simplifyProb(exp):
        if exp.type_ != 'prob':
            return exp

        exp.parts[0] = ProbabilityUtils.simplifyListOfVariables(exp.parts[0])

        if len(exp.parts) >= 2:
            exp.parts[1] = ProbabilityUtils.simplifyListOfVariables(
                exp.parts[1])
        if len(exp.parts) >= 3:
            exp.parts[2] = ProbabilityUtils.simplifyListOfVariables(
                exp.parts[2])
        if len(exp.parts) >= 4:
            exp.parts[3] = ProbabilityUtils.simplifyListOfVariables(
                exp.parts[3])

        if eu.isEmpty(exp.parts[0]):
            return None

        return exp

    @staticmethod
    def simplifyListOfVariables(listVars):
        if not isinstance(listVars, list):
            return listVars

        listVars = list(filter(lambda e: not eu.isEmpty(e), listVars))

        if len(listVars) == 0:
            return None

        return listVars

    @staticmethod
    def isConditional(exp):
        if exp.type_ != 'prob':
            return False

        if len(exp.parts) == 3:
            zPart = exp.parts[1]

            if isinstance(zPart, list) and len(zPart) > 0:
                return True

        return False
