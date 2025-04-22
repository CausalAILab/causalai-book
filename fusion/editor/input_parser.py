import functools

# from src.editor.classes.section import Section
from src.editor.classes.section_limit import SectionLimit
from src.editor.classes.parsing_error import ParsingError


def sortByNumber(a, b):
    return a - b


def sortBySectionOrder(a, b):
    return a.section.order - b.section.order


class InputParser():

    def __init__(self, sections=[]):
        self.sections = sections

    def parse(self, content):
        try:
            # divide the text into sections
            sectionLimits = []
            tagPositions = []
            missingRequiredTags = []

            for section in self.sections:
                tagLine = self.searchForLineWith(content, section.tag)

                if tagLine is not None:
                    tagPositions.append(tagLine)
                else:
                    if section.required:
                        missingRequiredTags.append(section.tag)

                sectionLimit = SectionLimit(section, tagLine, None)

                sectionLimits.append(sectionLimit)

            tagPositions = sorted(
                tagPositions, key=functools.cmp_to_key(sortByNumber))

            self.checkForInvalidTags(content, tagPositions)

            if len(missingRequiredTags) > 1:
                raise Exception('Please specify the tags: ' +
                                ', '.join(missingRequiredTags) + '.')
            elif len(missingRequiredTags) == 1:
                raise Exception('Please specify the tag: ' +
                                missingRequiredTags[0] + '.')

            i = 0

            for section in self.sections:
                if sectionLimits[i].start is not None:
                    sIdx = tagPositions.index(sectionLimits[i].start)

                    if sIdx == len(tagPositions) - 1:
                        sectionLimits[i].end = len(content.split('\n')) + 1
                    else:
                        sectionLimits[i].end = tagPositions[sIdx + 1] - 1

                i = i + 1

            # parse by section
            lines = content.split('\n')
            parsedData = {}

            sortedSectionLimits = sorted(
                sectionLimits, key=functools.cmp_to_key(sortBySectionOrder))

            for limits in sortedSectionLimits:
                if limits.start is not None:
                    sectionLines = lines[limits.start + 1: limits.end + 1]
                    sectionLines = list(
                        filter(lambda l: l is not None and l != '', sectionLines))

                    parsedData = limits.section.parse(sectionLines, parsedData)

                    if isinstance(parsedData, ParsingError):
                        raise ParsingError(
                            parsedData.message, parsedData.lineNumber + limits.start + 1)

            return parsedData
        except Exception as error:
            print(error.__str__())

    def searchForLineWith(self, content, text):
        lines = content.split('\n')

        for i in range(len(lines)):
            line = lines[i]

            if line.strip() == text:
                return i

        return None

    def checkForInvalidTags(self, content, recognizedTagsPosition):
        lines = content.split('\n')

        for i in range(len(lines)):
            line = lines[i]

            if line.startswith('<') and i not in recognizedTagsPosition:
                raise Exception(
                    'Please specify a valid tag (at line ' + str(i + 1) + ').')
