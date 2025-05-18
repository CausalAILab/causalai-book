from src.inference.classes.counterfactual import Counterfactual, Intervention
from src.inference.classes.expression import Expression
from src.inference.utils.graph_utils import compareNames

from src.inference.utils.graph_utils import GraphUtils as gu
from src.inference.utils.set_utils import SetUtils as su
from src.common.object_utils import ObjectUtils as ou


def isCtfEqual(a, b):
    if a is None and b is None:
        return True

    if a is None or b is None:
        return False

    if not su.equals([a.variable], [b.variable], 'name'):
        return False

    if len(a.interventions) != len(b.interventions):
        return False

    for aIntv in a.interventions:
        matching = list(filter(lambda intv: su.equals(
            [aIntv.variable], [intv.variable], 'name'), b.interventions))

        if len(matching) != 1:
            return False

        bIntv = matching[0]

        if not su.isEqual(aIntv.value, bIntv.value):
            return False

    return True


class CounterfactualUtils():

    # Counterfactual[]
    # Counterfactual[]

    @staticmethod
    def simplify(Ystar, G):
        Ystar = CounterfactualUtils.minimize(Ystar, G)

        for Yx in Ystar:
            # Yy s.t. Yy != y
            if len(Yx.interventions) == 1:
                intv = Yx.interventions[0]

                if su.equals([intv.variable], [Yx.variable], 'name') and not su.equals([intv.value], [Yx.value], 'name'):
                    return 0

            # Yx has multiple values
            matching = list(filter(lambda Wt: su.equals(
                [Wt.variable], [Yx.variable], 'name'), Ystar))
            values = list(map(lambda Wt: Wt.value, matching))
            values = su.unique(values)

            if len(values) >= 2:
                return 0

        indicesToRemove = []

        for i in range(len(Ystar)):
            if i in indicesToRemove:
                continue

            Yx = Ystar[i]

            # multiple occurences of Yx = a
            # bug: isEqual compares object references, not the contents of interventions
            indices = [j for j in range(len(Ystar)) if i != j and su.equals(
                [Ystar[j].variable], [Yx.variable], 'name') and su.isEqual(Ystar[j].interventions, Yx.interventions) and su.isEqual(Ystar[j].value, Yx.value)]

            if len(indices) > 0:
                indicesToRemove.extend(indices)

            # multiple occurences of Yy = y
            if len(Yx.interventions) == 1:
                intv = Yx.interventions[0]

                if su.equals([intv.variable], [Yx.variable], 'name') and su.isEqual(intv.value, Yx.value):
                    indices = [j for j in range(len(Ystar)) if i != j and su.equals(
                        [Ystar[j].variable], [Yx.variable], 'name') and su.isEqual(Ystar[j].interventions, Yx.interventions) and su.isEqual(Ystar[j].value, Yx.value)]

                    if len(indices) > 0:
                        indicesToRemove.extend(indices)

        indicesToKeep = [i for i in range(
            len(Ystar)) if i not in indicesToRemove]
        Ystar = list(map(lambda i: Ystar[i], indicesToKeep))

        return Ystar

    # Counterfactual[], Graph
    # Counterfactual[]

    @staticmethod
    def minimize(Ystar, G):
        Ystar = ou.makeArray(Ystar)

        for Yx in Ystar:
            X = []

            for intv in Yx.interventions:
                X.append(intv)

            VX = CounterfactualUtils.V(X)

            GbarX = gu.transform(G, VX, None)
            AnY = gu.ancestors(CounterfactualUtils.V(Yx), GbarX)
            T = su.intersection(VX, AnY, 'name')

            intvs = []

            for intv in Yx.interventions:
                if su.belongs(intv.variable, T, compareNames):
                    intvs.append(intv)

            Yx.interventions = intvs

        return Ystar

    # Counterfactual[]
    # Counterfactual[]

    @staticmethod
    def unnest(Ystar):
        unnestedYstar = []
        summed = []

        for Yx in Ystar:
            CounterfactualUtils.__unnest(Yx, unnestedYstar, summed)

        return unnestedYstar, summed

    # Counterfactual, Counterfactual[], Node[]

    @staticmethod
    def __unnest(Yx, unnestedYstar, summed):
        X = Yx.interventions

        for x in X:
            if type(x.value) is not Counterfactual:
                continue

            summed.append(x.variable)
            Yxprime = ou.clone(x.value)
            Yxprime.value = x.variable
            x.value = x.variable

            CounterfactualUtils.__unnest(Yxprime, unnestedYstar, summed)

        unnestedYstar.append(Yx)

    # Counterfactual[], Graph
    # Counterfactual[]

    @staticmethod
    def factorize(Ystar, G):
        Wstar = []

        for Yx in Ystar:
            intvsToAdd = []

            Pa = gu.parents(CounterfactualUtils.V(Yx), G)
            Z = su.difference(Pa, su.union(CounterfactualUtils.V(
                Yx.interventions), [Yx.variable], 'name'), 'name')

            for z in Z:
                intv = Intervention(z)
                intvsToAdd.append(intv)

            Wx = Counterfactual(Yx.variable, Yx.value,
                                su.union(Yx.interventions, intvsToAdd))
            Wstar.append(Wx)

        return Wstar

    # Counterfactual[]
    # bool

    @staticmethod
    def isConsistent(Ystar):
        VY = CounterfactualUtils.V(Ystar)

        for Wt in Ystar:
            for intv in Wt.interventions:
                if not su.belongs(intv.variable, VY, compareNames):
                    continue

                for Yx in Ystar:
                    if Wt == Yx:
                        continue

                    if not su.equals([intv.variable], [Yx.variable], 'name'):
                        continue

                    if intv.value != Yx.value:
                        return False

        for Ws in Ystar:
            for Wt in Ystar:
                if Ws == Wt:
                    continue

                for s in Ws.interventions:
                    matching = list(filter(lambda intv: su.equals(
                        [s.variable], [intv.variable], 'name'), Wt.interventions))

                    for t in matching:
                        if s.value != t.value:
                            return False

        return True

    @staticmethod
    def getAncestralComponents(Ystar, Xstar, G):
        Xstar = CounterfactualUtils.minimize(Xstar, G)

        A = []

        for Yx in Ystar:
            AnYx = CounterfactualUtils.An(Yx, G)
            XAnY = list(filter(lambda x: su.belongs(
                x, AnYx, isCtfEqual), Xstar))
            VXAnY = CounterfactualUtils.V(XAnY)
            Gunderbar = gu.transform(G, None, VXAnY)
            Ai = CounterfactualUtils.An(Yx, Gunderbar)
            A.append(Ai)

        return A

    # Counterfactual[], Graph
    # Counterfactual[][]

    @staticmethod
    def cComponents(Ystar, G):
        CC = gu.cCompDecomposition(G)
        C = []

        for CCi in CC:
            Ci = []

            for v in CCi:
                matching = list(filter(lambda Yx: su.equals(
                    CounterfactualUtils.V(Yx), [v], 'name'), Ystar))

                Ci.extend(matching)

            C.append(Ci)

        return C

    # Counterfactual[], Graph
    # Counterfactual[]
    @staticmethod
    def An(Ystar, G):
        Ystar = ou.makeArray(Ystar)

        A = []

        for Yx in Ystar:
            if Yx.interventions is None or len(Yx.interventions) == 0:
                Y = CounterfactualUtils.V(Yx)
                W = gu.ancestors(Y, G)
                WminusY = su.difference(W, Y, 'name')

                for w in WminusY:
                    ctf = Counterfactual(w)
                    A.append(ctf)

                A.append(Yx)
            else:
                X = Yx.interventions
                Y = CounterfactualUtils.V(Yx)
                VX = CounterfactualUtils.V(X)
                GXbar = gu.transform(G, None, VX)
                GbarX = gu.transform(G, VX, None)
                W = gu.ancestors(Y, GXbar)
                WminusY = su.difference(W, Y, 'name')

                for w in WminusY:
                    Z = su.intersection(VX, gu.ancestors(w, GbarX), 'name')

                    intvs = []

                    for z in Z:
                        zValue = None

                        matches = list(
                            filter(lambda x: su.equals([x.variable], [z], 'name'), X))

                        if len(matches) > 0:
                            zValue = matches[0].value

                        intv = Intervention(z, zValue)
                        intvs.append(intv)

                    Wz = Counterfactual(w, None, intvs)
                    A.append(Wz)

                A.append(Yx)

        A = su.uniqWith(A, isCtfEqual)

        return A

    @staticmethod
    def V(Ystar):
        Ystar = ou.makeArray(Ystar)

        return list(map(lambda w: w.variable, Ystar))

    @staticmethod
    def write(Ystar):
        Ystar = ou.makeArray(Ystar)

        ctfs = []

        for Yx in Ystar:
            text = Yx.variable['name'] if Yx.variable is not None else ''

            intvsText = []

            for intv in Yx.interventions:
                intvText = intv.variable['name'] if intv.variable is not None else ''
                intvText = intvText + ' = '

                if intv.value is not None:
                    if type(intv.value) is int or type(intv.value) is float:
                        intvText = intvText + str(intv.value)
                    elif type(intv.value) is dict and 'name' in intv.value:
                        intvText = intvText + intv.value['name'].lower()
                    elif type(intv.value) is Counterfactual:
                        intvText = intvText + \
                            CounterfactualUtils.write(intv.value)
                    else:
                        intvText = intvText + intv.value
                else:
                    intvText = intvText + intv.variable['name'].lower()

                intvsText.append(intvText)

            if len(intvsText) > 0:
                text = text + '_{' + ', '.join(intvsText) + '}'

            text = text + ' = '

            if Yx.value is not None:
                if type(Yx.value) is int or type(Yx.value) is float:
                    text = text + str(Yx.value)
                elif type(Yx.value) is dict and 'name' in Yx.value:
                    text = text + Yx.value['name'].lower()
                else:
                    text = text + Yx.value
            else:
                text = text + (Yx.variable['name'].lower()
                               if Yx.variable is not None else '')

            ctfs.append(text)

        return ', '.join(ctfs)

    @staticmethod
    def print(Ystar):
        Ystar = ou.makeArray(Ystar)

        ctfs = []

        for Yx in Ystar:
            text = Yx.variable['name'] if Yx.variable is not None else ''

            intvsText = []

            for intv in Yx.interventions:
                intvText = intv.variable['name'] if intv.variable is not None else ''
                intvText = intvText + ' = '

                if intv.value is not None:
                    if type(intv.value) is int or type(intv.value) is float:
                        intvText = intvText + str(intv.value)
                    elif type(intv.value) is dict and 'name' in intv.value:
                        intvText = intvText + intv.value['name'].lower()
                    else:
                        intvText = intvText + intv.value
                else:
                    intvText = intvText + intv.variable['name'].lower()

                intvsText.append(intvText)

            if len(intvsText) > 0:
                text = text + '_{' + ', '.join(intvsText) + '}'

            text = text + ' = '

            if Yx.value is not None:
                if type(Yx.value) is int or type(Yx.value) is float:
                    text = text + str(Yx.value)
                elif type(Yx.value) is dict and 'name' in Yx.value:
                    text = text + Yx.value['name'].lower()
                else:
                    text = text + Yx.value
            else:
                text = text + (Yx.variable['name'].lower()
                               if Yx.variable is not None else '')

            ctfs.append(text)

        print(', '.join(ctfs))

    @staticmethod
    def assignValues(exp, ctf, summed):
        if not isinstance(exp, Expression):
            return CounterfactualUtils.assignPart(exp, ctf, summed)

        substitueFunction = functionSwitch.get(exp.type_, lambda: None)

        if substitueFunction is None:
            return exp

        return substitueFunction(exp, ctf, summed)

    @staticmethod
    def assignPart(exp, ctf, summed):
        if exp is None:
            return exp

        if isinstance(exp, str):
            return exp

        if isinstance(exp, Expression):
            return CounterfactualUtils.assignValues(exp, ctf, summed)

        if isinstance(exp, list):
            parts = []

            for part in exp:
                parts.append(
                    CounterfactualUtils.assignPart(part, ctf, summed))

            return parts

        if 'label' in exp:
            value = CounterfactualUtils.findValue(exp, ctf)

            if value is None:
                if su.belongs(exp, summed, compareNames):
                    value = exp['label'].lower()
                else:
                    return exp
            else:
                if type(value) is int or type(value) is float:
                    value = str(value)
                elif type(value) is dict and 'label' in value:
                    value = value['label'].lower()

            exp = Expression('=', [exp, value])

            return exp

        if 'name' in exp:
            value = CounterfactualUtils.findValue(exp, ctf)

            if value is None:
                if su.belongs(exp, summed, compareNames):
                    value = exp['name'].lower()
                else:
                    return exp
            else:
                if type(value) is int or type(value) is float:
                    value = str(value)
                elif type(value) is dict and 'name' in value:
                    value = value['name'].lower()

            exp = Expression('=', [exp, value])

            return exp

        return exp

    @staticmethod
    def findValue(node, ctf):
        for Yx in ctf:
            if su.equals([Yx.variable], [node], 'name'):
                return Yx.value

            for intv in Yx.interventions:
                if su.equals([intv.variable], [node], 'name'):
                    return intv.value

        return None


def substituteProb(exp, ctf, summed):
    parts = []

    for part in exp.parts:
        parts.append(CounterfactualUtils.assignPart(part, ctf, summed))

    exp.parts = parts

    return exp


def substituteProduct(exp, ctf, summed):
    parts = []

    for part in exp.parts:
        parts.append(CounterfactualUtils.assignPart(part, ctf, summed))

    exp.parts = parts

    return exp


def substituteFrac(exp, ctf, summed):
    parts = []

    for part in exp.parts:
        parts.append(CounterfactualUtils.assignPart(part, ctf, summed))

    exp.parts = parts

    return exp


def substituteSum(exp, ctf, summed):
    exp.parts[2] = CounterfactualUtils.assignPart(exp.parts[2], ctf, summed)

    return exp


def substituteEquals(exp, ctf, summed):
    return exp


def substituteDefault(exp, ctf, summed):
    return exp


functionSwitch = {
    'sum': substituteSum,
    'product': substituteProduct,
    'concat': substituteProduct,
    'prob': substituteProb,
    # 'indep': writeIndep,
    'frac': substituteFrac,
    # '+': writePlus,
    # '-': writeMinus,
    '=': substituteEquals,
    # '!=': writeNotEquals,
    # '()': writeParentheses,
    # '{}': writeBraces,
    # 'text': writeText,
    # 'list': writeList,
    # 'script': writeScript,
    # 'color': substituteDefault,
    # 'counterfact': substituteDefault,
    # 'coef': writeCoef
}
