from typing import List, Dict
import sympy as sp

class SymbolContainer:
    def __init__(self, symbols: List[sp.Symbol] = [], syn: Dict[sp.Symbol, sp.Symbol] = {}):
        self.symbol_list = list(symbols)
        self.symbol_dict = {str(s): sx for s, sx in syn.items()} if len(syn) > 0 else {str(s): s for s in symbols}


    def __len__(self):
        return len(self.symbol_list)
    
    def __getitem__(self, key):
        if(isinstance(key, int)):
            return self.symbol_list[key]
        if(isinstance(key, str)):
            return self.symbol_dict[key]
        if(isinstance(key,list)):
            if(all(isinstance(k,int) for k in key)):
                return [self.symbol_list[k] for k in key]
            if(all(isinstance(k,str) for k in key)):
                return [self.symbol_dict[k] for k in key]
        if(isinstance(key, slice)):
            start, stop, step = key.indices(len(self.symbol_list))
            return [self.symbol_list[i] for i in range(start, stop, step)]

        
        raise KeyError("Key must be an integer or a string")
    

    def __getattr__(self, key):
        if(key in self.symbol_dict.keys()):
            return self.symbol_dict[key]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __repr__(self):
        return repr(self.symbol_list)
    
    def __iter__(self):
        return iter(self.symbol_list)
    
    def __add__(self, other):
        return self.symbol_list + other.symbol_list
    
    def __subtract__(self, other):
        return self.symbol_list - other.symbol_list