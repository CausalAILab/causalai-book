


class ReadOnly:
    def __init__(self, obj, banned_attrs = []):
        self.obj = obj
        self._banned_attrs = banned_attrs


    def __get__attr(self, attr):
        if attr in self._banned_attrs:
            raise AttributeError(f"Attribute {attr} is not accessible")
        return getattr(self._obj, attr)