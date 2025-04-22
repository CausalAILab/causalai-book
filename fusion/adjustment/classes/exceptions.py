class AdjustmentSetsError(Exception):

    def __init__(self, message = '', witness = None):
        self.message = message
        self.witness = witness


    def __str__(self):
        return 'AdjustmentSetsError: ' + self.message + ', witness: ' + str(self.witness)


    def __repr__(self):
        # return '{\'message\': self.message, \'witness\': self.witness}'
        return '{\'message\': ' + self.message + ', \'witness\': ' + str(self.witness) + '}'