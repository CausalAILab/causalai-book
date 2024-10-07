from numbers import Number

from src.editor.classes.section import Section

class SectionLimit():

    section = Section
    start = Number
    end = Number

    def __init__(self, section = None, start = None, end = None):
        self.section = section
        self.start = start
        self.end = end