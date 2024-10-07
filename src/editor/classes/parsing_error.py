from numbers import Number


class ParsingError(Exception):

    message = str
    lineNumber = Number

    def __init__(self, message, lineNumber = 0):
        self.message = message
        self.lineNumber = lineNumber