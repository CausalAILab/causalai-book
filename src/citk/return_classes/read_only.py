


class ReadOnly:
    """
    A class that wraps an object and makes its attributes read-only.
    """
    
    
    def __init__(self, obj, banned_attrs = []):
        self._obj = obj
        self._banned_attrs = banned_attrs


    def __getattr__(self, attr):
        if attr in self._banned_attrs:
            raise AttributeError(f"Attribute {attr} is not accessible")
        return getattr(self._obj, attr)