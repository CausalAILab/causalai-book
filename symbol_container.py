from typing import List, Dict
import sympy as sp

class SymbolContainer:
    def __init__(self, symbols: List[sp.Symbol] = None, syn: Dict[sp.Symbol, sp.Symbol] = None):
        if symbols is None:
            symbols = []
        if syn is None:
            syn = {}
        
        self.symbol_list = list(symbols)
        # Here, using the union of two dictionaries to give precedence as you desire.
        self.symbol_dict = {str(s): s for s in symbols} | {str(k): v for k, v in syn.items()}
        self.symbol_set = set(self.symbol_list)
    
    def __len__(self):
        return len(self.symbol_list)
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.symbol_list[key]
        if isinstance(key, str):
            return self.symbol_dict[key]
        if isinstance(key, list):
            if all(isinstance(k, int) for k in key):
                return [self.symbol_list[k] for k in key]
            if all(isinstance(k, str) for k in key):
                return [self.symbol_dict[k] for k in key]
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self.symbol_list))
            return [self.symbol_list[i] for i in range(start, stop, step)]
        raise KeyError("Key must be an integer or a string")
    
    def __getattr__(self, key):
        if key in self.symbol_dict:
            return self.symbol_dict[key]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __repr__(self):
        return repr(self.symbol_list)
    
    def __iter__(self):
        return iter(self.symbol_list)
    
    def __add__(self, other):
        if isinstance(other, list):
            return self.symbol_list + other
        if isinstance(other, set):
            # For sets, treat + as union.
            return self.symbol_set | other
        if isinstance(other, SymbolContainer):
            return self.symbol_list + other.symbol_list
        raise TypeError(f"Unsupported operand type(s) for +: 'SymbolContainer' and '{type(other)}'")
    
    def __radd__(self, other):
        # Right-hand addition: reverse the order.
        if isinstance(other, list):
            return other + self.symbol_list
        if isinstance(other, set):
            return other | self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_list + self.symbol_list
        raise TypeError(f"Unsupported operand type(s) for +: '{type(other)}' and 'SymbolContainer'")
    
    def __sub__(self, other):
        if isinstance(other, list):
            return self.symbol_set - set(other)
        if isinstance(other, set):
            return self.symbol_set - other
        if isinstance(other, SymbolContainer):
            return self.symbol_set - other.symbol_set
        raise TypeError(f"Unsupported operand type(s) for -: 'SymbolContainer' and '{type(other)}'")
    
    def __rsub__(self, other):
        # Reverse subtraction: other - self.symbol_set
        if isinstance(other, list):
            return set(other) - self.symbol_set
        if isinstance(other, set):
            return other - self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set - self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for -: '{type(other)}' and 'SymbolContainer'")
    
    def __and__(self, other):
        if isinstance(other, set):
            return self.symbol_set & other
        if isinstance(other, SymbolContainer):
            return self.symbol_set & other.symbol_set
        raise TypeError(f"Unsupported operand type(s) for &: 'SymbolContainer' and '{type(other)}'")
    
    def __rand__(self, other):
        # Reverse intersection: ensure the left-hand (other) value is handled correctly.
        if isinstance(other, set):
            return other & self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set & self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for &: '{type(other)}' and 'SymbolContainer'")
    
    def __or__(self, other):
        if isinstance(other, set):
            return self.symbol_set | other
        if isinstance(other, SymbolContainer):
            return self.symbol_set | other.symbol_set
        raise TypeError(f"Unsupported operand type(s) for |: 'SymbolContainer' and '{type(other)}'")
    
    def __ror__(self, other):
        # Reverse union: when SymbolContainer is on the right.
        if isinstance(other, set):
            return other | self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set | self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for |: '{type(other)}' and 'SymbolContainer'")
    
    def __eq__(self, other):
        if isinstance(other, set):
            return self.symbol_set == other
        if isinstance(other, list):
            return self.symbol_list == other
        if isinstance(other, SymbolContainer):
            return self.symbol_set == other.symbol_set
        return False
    
    def __req__(self, other):
        # Equality is symmetric so this just defers to __eq__.
        return self.__eq__(other)

    def __contains__(self, item):
        return item in self.symbol_set
    
    
    def __hash__(self):
        return hash(frozenset(self.symbol_set))
    