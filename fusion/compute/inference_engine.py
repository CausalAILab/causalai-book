from src.inference.engines.backdoor_engine import BackdoorEngine
from src.inference.engines.generalized_adjustment_engine import GeneralizedAdjustmentEngine
from src.inference.engines.ST_engine import STEngine
from src.inference.engines.do_calculus_engine import DoCalculusEngine
from src.inference.engines.selection_bias_engine import SelectionBiasEngine
from src.inference.engines.counterfactual_engine import CounterfactualEngine
from src.inference.engines.sigma_calculus_engine import SigmaCalculusEngine
from src.transportability.classes.transportability import targetPopulation
from src.inference.classes.expression import Expression
from src.inference.classes.failure import Failure

from src.inference.utils.expression_utils import ExpressionUtils as eu

from src.error.error_messages import defaultErrorMessage


class InferenceEngine():

    @staticmethod
    def compute(query, G, config):
        if not query or not G:
            raise Exception(defaultErrorMessage)

        engines = InferenceEngine.getUsableEngines(query, G, config)

        if len(engines) == 0:
            raise Exception(defaultErrorMessage)

        computeResult = InferenceEngine.__compute(query, G, config, engines)

        return computeResult

    @staticmethod
    def getUsableEngines(query, G, config):
        # engines = [GeneralizedAdjustmentEngine(), STEngine(
        # ), DoCalculusEngine(), SelectionBiasEngine(), CounterfactualEngine(), SigmaCalculusEngine()]
        engines = [GeneralizedAdjustmentEngine(), STEngine(
        ), DoCalculusEngine(), SelectionBiasEngine(), CounterfactualEngine()]

        bdEngine = BackdoorEngine()
        bdEngineCanCompute = bdEngine.canCompute(query, G, config)

        if bdEngineCanCompute:
            engines.insert(0, bdEngine)

        return list(filter(lambda e: e.canCompute(query, G, config), engines))

    @staticmethod
    def __compute(query, G, config, engines):
        computed = list(map(lambda e: e.compute(query, G, config), engines))
        computed = list(filter(lambda r: r is not None, computed))

        positiveResults = list(
            filter(lambda r: isinstance(r, Expression), computed))
        negativeResults = list(
            filter(lambda r: isinstance(r, Failure), computed))

        if len(positiveResults) > 0:
            # query can include soft intervention
            populations = config['populations'] if 'populations' in config else [
                targetPopulation]
            queryExpression = eu.create(
                'prob', [query.y, query.z, query.x, '\*' if len(populations) > 1 else None])
            result = positiveResults[0]

            return eu.create('=', [queryExpression, result])
        else:
            result = negativeResults[0]

            return result

    @staticmethod
    def printResult(exp, removeWhitespace=False):
        if isinstance(exp, Expression):
            result = eu.write(exp)

            if removeWhitespace:
                print(result.replace(' ', ''))
            else:
                print(result)
        elif isinstance(exp, Failure):
            result = eu.write(exp.message)

            if removeWhitespace:
                print(result.replace(' ', ''))
            else:
                print(result)
