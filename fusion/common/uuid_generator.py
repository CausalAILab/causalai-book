import string
import random


class UUIDGenerator():

    @staticmethod
    def generateRandomId(length):
        return UUIDGenerator.randomString(length)

    @staticmethod
    def randomString(length):
        return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(length))