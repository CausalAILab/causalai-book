from src.inference.classes.counterfactual import Counterfactual
from src.inference.classes.expression import Expression
# from src.inference.classes.variable import Variable
from src.inference.classes.failure import Failure
from src.inference.utils.counterfactual_utils import CounterfactualUtils


class ExpressionUtils():

    @staticmethod
    def create(type_, parts):
        return Expression(type_, parts)

    @staticmethod
    def isEmpty(exp):
        if exp is None:
            return True

        if isinstance(exp, str) and exp == '':
            return True

        # if isinstance(exp, Variable) and (exp.name is None or exp.name == ''):
        #     return True

        if isinstance(exp, list) and len(exp) == 0:
            return True

        return False

# maybe implement __eq__ in Expression class?

    @staticmethod
    def isEqual(e1, e2):
        return False

#     static isEqual(exp1: any, exp2: any): boolean {
#         return _.isEqualWith(exp1, exp2, (p1, p2) => {
#             if (p1 && p2 && p1.name && p2.name)
#                 return p1.name == p2.name;
#         });
#     }

    @staticmethod
    def write(exp, options=None):
        if not isinstance(exp, Expression):
            return ExpressionUtils.writePart(exp, options)

        writeFunction = writeSwitcher.get(exp.type_, lambda: None)

        if writeFunction is None:
            return ''

        return writeFunction(exp, options)

    @staticmethod
    def writePart(exp, options=None):
        if exp is None:
            return ''

        if isinstance(exp, str):
            return exp

        if isinstance(exp, Expression):
            return ExpressionUtils.write(exp, options)

        if isinstance(exp, Failure):
            return ExpressionUtils.write(exp.message, options)

        if isinstance(exp, Counterfactual):
            return CounterfactualUtils.write(exp)

        if isinstance(exp, list):
            parts = []

            for part in exp:
                parts.append(ExpressionUtils.writePart(part, options))

            return ','.join(parts)

        if 'label' in exp:
            return exp['label']

        if 'name' in exp:
            return exp['name']

        # if isinstance(exp, Variable):
        #     if exp.label is not None:
        #         return exp.label

        #     if exp.name is not None:
        #         return exp.name

        return ''


def writeProb(exp, options=None):
    result = 'P'
    doExpList = None

    # subscript
    if len(exp.parts) >= 3 and exp.parts[2] is not None:
        if len(exp.parts[2]) > 0:
            strList = []

            for part in exp.parts[2]:
                if type(part) is dict and 'label' in part:
                    strList.append('do(' + part['label'] + ')')
                elif type(part) is Expression:
                    strList.append('do(' + ExpressionUtils.write(part) + ')')
                elif type(part) is Counterfactual:
                    strList.append(CounterfactualUtils.write(part))
                else:
                    strList.append('do(' + part + ')')

            doExpression = ', '.join(strList)

            doExpList = ExpressionUtils.create('list', [doExpression])

        else:
            result = result + \
                '_{' + ExpressionUtils.writePart(exp.parts[2], options) + '}'

    # superscript
    if len(exp.parts) >= 4 and exp.parts[3] is not None:
        result = result + \
            '^{' + ExpressionUtils.writePart(exp.parts[3], options) + '}'

    result = result + '\\left(' + \
        ExpressionUtils.writePart(exp.parts[0], options)

    # add do expressions to conditional part
    if doExpList is not None:
        if len(exp.parts) >= 2 and not ExpressionUtils.isEmpty(exp.parts[1]):
            doExpList.parts.append(exp.parts[1])

        result = result + ' \\middle| ' + \
            ExpressionUtils.writePart(doExpList, options)

    else:
        if len(exp.parts) >= 2 and not ExpressionUtils.isEmpty(exp.parts[1]):
            result = result + ' \\middle| ' + \
                ExpressionUtils.writePart(exp.parts[1], options)

    # interventions separated by semi-colon
    # sigma_AB, sigma^1_C: exp.parts[4] has two entries: [[A,B],[]] and [[C],[]]
    # 1st entry: list of node/strings for subscript
    # 2nd entry: list of node/strings for superscript
    sigmasExp = None

    if len(exp.parts) >= 5 and exp.parts[4] is not None:
        if len(exp.parts[4]) > 0:
            sigmaExps = []

            for part in exp.parts[4]:
                # no superscript
                if len(part) >= 1:
                    # no nodes are being intervened, so skip
                    if len(part[0]) == 0:
                        continue

                    subscriptNames = ExpressionUtils.writePart(
                        part[0], options)
                    sigmaExp = '\\sigma_{' + subscriptNames + '}'

                    # with superscript
                    if len(part) >= 2:
                        superscriptNames = ExpressionUtils.writePart(
                            part[1], options)
                        sigmaExp = sigmaExp + '^{' + superscriptNames + '}'

                    sigmaExps.append(sigmaExp)

            sigmasExp = ExpressionUtils.create('list', [', '.join(sigmaExps)])

    doExpExists = doExpList is not None
    # condExpExists = len(
    #     exp.parts) >= 2 and not ExpressionUtils.isEmpty(exp.parts[1])

    if sigmasExp is not None and not doExpExists:
        # if condExpExists:
        #     result = result + ','

        result = result + '; ' + ExpressionUtils.writePart(sigmasExp, options)

    result = result + '\\right)'

    return result


def writeIndep(exp, options=None):
    result = '\\left('

    if exp.parts[0] is not None:
        result = result + \
            ExpressionUtils.writePart(exp.parts[0], options) + ' \\perp '

    if len(exp.parts) > 1 and exp.parts[1] is not None:
        result = result + ExpressionUtils.writePart(exp.parts[1], options)

    if len(exp.parts) > 2 and exp.parts[2] is not None:
        result = result + ' | ' + \
            ExpressionUtils.writePart(exp.parts[2], options)

    result = result + '\\right)'

    if len(exp.parts) > 3 and exp.parts[3] is not None:
        result = result + \
            '_{' + ExpressionUtils.writePart(exp.parts[3], options) + '}'

    return result


def writeSum(exp, options=None):
    if ExpressionUtils.isEmpty(exp.parts[0]):
        return ExpressionUtils.writePart(exp.parts[2], options)

    result = '\\sum'

    if exp.parts[0] is not None:
        result = result + \
            '_{' + ExpressionUtils.writePart(exp.parts[0], options) + '}'

    if exp.parts[1] is not None:
        result = result + \
            '^{' + ExpressionUtils.writePart(exp.parts[1], options) + '}'

    result = result + \
        '{' + ExpressionUtils.writePart(exp.parts[2], options) + '}'

    return result


def writeProduct(exp, options=None):
    parts = []

    for part in exp.parts:
        parts.append(ExpressionUtils.writePart(part, options))

    return ''.join(parts)


def writeFrac(exp, options=None):
    return '\\frac{' + ExpressionUtils.writePart(exp.parts[0], options) + '}{' + ExpressionUtils.writePart(exp.parts[1], options) + '}'


def writePlus(exp, options=None):
    parts = []

    for part in exp.parts:
        parts.append(ExpressionUtils.writePart(part, options))

    return ' + '.join(parts)


def writeMinus(exp, options=None):
    parts = []

    for part in exp.parts:
        parts.append(ExpressionUtils.writePart(part, options))

    return ' - '.join(parts)


def writeEquals(exp, options=None):
    return ExpressionUtils.writePart(exp.parts[0], options) + ' = ' + ExpressionUtils.writePart(exp.parts[1], options)


def writeNotEquals(exp, options=None):
    return ExpressionUtils.writePart(exp.parts[0], options) + ' \\neq ' + ExpressionUtils.writePart(exp.parts[1], options)


def writeParentheses(exp, options=None):
    return '\\left(' + ExpressionUtils.writePart(exp.parts[0], options) + '\\right)'


def writeBraces(exp, options=None):
    return '\\left\\{' + ExpressionUtils.writePart(exp.parts[0], options) + '\\right\\}'


def writeText(exp, options=None):
    parts = []

    for p in exp.parts:
        parts.append(ExpressionUtils.writePart(p, options))

    return '\\text{' + ' '.join(parts) + '}'


def writeList(exp, options=None):
    parts = []

    for p in exp.parts:
        parts.append(ExpressionUtils.writePart(p, options))

    return ', '.join(parts)


def writeScript(exp, options=None):
    result = ExpressionUtils.writePart(exp.parts[0], options)

    # subscript
    if len(exp.parts) >= 2 and exp.parts[1] is not None:
        # let subscriptsToHide = options && options.hideSubscript ? options.hideSubscript : null;
        # let hideSubscript: boolean = false;

        # if (subscriptsToHide) {
        #     if (typeof exp.parts[1] == 'string') {
        #         if (subscriptsToHide[exp.parts[1]] !== undefined)
        #             hideSubscript = true;

        #         let scriptWithoutParenthesis: string = exp.parts[1].replace('(', '').replace(')', '');

        #         if (subscriptsToHide[scriptWithoutParenthesis] !== undefined)
        #             hideSubscript = true;
        #     }
        # }

        # if (!hideSubscript)
        #     exp = exp + '_{' + this.writePart(exp.parts[1], options) + '}';

        result = result + \
            '_{' + ExpressionUtils.writePart(exp.parts[1], options) + '}'

    # superscript
    if len(exp.parts) >= 3 and exp.parts[2] is not None:
        # let superscriptsToHide = options && options.hideSuperscript ? options.hideSuperscript : null;
        # let hideSuperscript: boolean = false;

        # if (superscriptsToHide) {
        #     if (typeof exp.parts[2] == 'string') {
        #         if (superscriptsToHide[exp.parts[2]] !== undefined)
        #             hideSuperscript = true;

        #         let scriptWithoutParenthesis: string = exp.parts[2].replace('(', '').replace(')', '');

        #         if (superscriptsToHide[scriptWithoutParenthesis] !== undefined)
        #             hideSuperscript = true;
        #     }
        # }

        # if (!hideSuperscript)
        #     exp = exp + '^{' + this.writePart(exp.parts[2], options) + '}';

        result = result + \
            '^{' + ExpressionUtils.writePart(exp.parts[2], options) + '}'

    return result


def writeCoef(exp, options=None):
    result = '\\' + exp.parts[0] + '_{'

    parts = []

    for i in range(1, len(exp.parts)):
        p = exp.parts[i]
        parts.append(ExpressionUtils.writePart(p, options))

    result = result + ''.join(parts) + '}'

    return result


#             case 'color': {
#                 return "{\\color{" + expression.parts[0] + "}{" + this.writePart(expression.parts[1], options) + "}}"
#             }
#             case 'countfact': {
#                 return "{" + this.writePart(expression.parts[0], options) + "}" +
#                     (expression.parts[1] && expression.parts[1].length != 0 ? "_{\\left[" + this.writePart(expression.parts[1], options) + "\\right]}" : '') +
#                     (expression.parts[2] ? "=" + this.writePart(expression.parts[2], options) : "");
#             }
#             case 'coef': {
#                 let exp: string = "\\" + expression.parts[0] + "_{";
#                 let parts: string[] = [];

#                 for (let i = 1; i < expression.parts.length; i++) {
#                     parts.push(this.writePart(expression.parts[i], options));
#                 }

#                 exp += parts.join('') + '}';

#                 return exp;
#             }
#         }
#     }

def writeDefault(exp, options=None):
    return ''


writeSwitcher = {
    'sum': writeSum,
    'product': writeProduct,
    'concat': writeProduct,
    'prob': writeProb,
    'indep': writeIndep,
    'frac': writeFrac,
    '+': writePlus,
    '-': writeMinus,
    '=': writeEquals,
    '!=': writeNotEquals,
    '()': writeParentheses,
    '{}': writeBraces,
    'text': writeText,
    'list': writeList,
    'script': writeScript,
    'color': writeDefault,
    'counterfact': writeDefault,
    'coef': writeCoef
}
