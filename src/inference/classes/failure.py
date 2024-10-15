from typing import Union, Any

from src.inference.classes.expression import Expression


class Failure(Exception):

    message: Union[str, Expression]
    witness: Any

    def __init__(self, message, witness):
        self.message = message
        self.witness = witness


    def __str__(self):
        return 'Failure: ' + str(self.message) + ', witness: ' + str(self.witness)


    def __repr__(self):
    #     # return '{\'message\': self.message, \'witness\': self.witness}'
        return '{\'message\': ' + str(self.message) + ', \'witness\': ' + str(self.witness) + '}'