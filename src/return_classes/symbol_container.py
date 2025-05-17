

from typing import List, Dict, Set, Union
import sympy as sp



class SymbolContainer:
    """
    A container for managing a collection of sympy.Symbols with various operations.

    Attributes
    ----------
    symbol_list : List['Variable']
        A list of sympy.Symbols stored in the container.
    symbol_dict : Dict[str, 'Variable']
        A dictionary mapping string representations of symbols to their corresponding sympy.Symbols.
    symbol_set : Set['Variable']
        A set of sympy.Symbols stored in the container for efficient set operations.

    Methods
    -------
    __len__() -> int
        Returns the number of symbols in the container.
    __getitem__(key) -> Union['Variable', List['Variable']]
        Retrieves a symbol or a list of symbols by index or name.
    __getattr__(key) -> 'Variable'
        Access a symbol by its string name.
    __repr__() -> str
        Returns a string representation of the container's symbol list.
    __iter__() -> iter
        Returns an iterator over the symbol list.
    __add__(other) -> Union[List['Variable'], Set['Variable']]
        Adds symbols from another container, list, or set.
    __radd__(other) -> Union[List['Variable'], Set['Variable']]
        Reverse add operation for lists, sets, or containers.
    __sub__(other) -> Set['Variable']
        Subtracts symbols from another container, list, or set.
    __rsub__(other) -> Set['Variable']
        Reverse subtraction operation.
    __and__(other) -> Set['Variable']
        Computes the intersection with another container, list, or set.
    __rand__(other) -> Set['Variable']
        Reverse intersection operation for containers and sets.
    __or__(other) -> Set['Variable']
        Computes the union with another container, list, or set.
    __ror__(other) -> Set['Variable']
        Reverse union operation for containers and sets.
    __eq__(other) -> bool
        Checks equality with another container, list, or set.
    __req__(other) -> bool
        Reverse equality check (symmetric equality).
    __contains__(item) -> bool
        Checks if a symbol is contained in the container.
    __hash__() -> int
        Returns the hash of the container (based on its symbols).
    """

    def __init__(self, symbols: List['Variable'] = None):
        """
        Initializes the SymbolContainer with a list of symbols and an optional dictionary of synonym mappings.
        
        Parameters
        ----------
        symbols : List['Variable'], optional
            A list of sympy.Symbols to initialize the container (default is an empty list).
        """
        
        if symbols is None:
            symbols = []
        
        self.symbol_list = list(symbols)
        self.symbol_dict = {}
        for symbol in symbols:
            if self.symbol_dict.get(symbol.main) is None:
                self.symbol_dict[symbol.main] = symbol
            elif isinstance(self.symbol_dict[symbol.main], list):
                self.symbol_dict[symbol.main].append(symbol)
            else:
                self.symbol_dict[symbol.main] = [self.symbol_dict[symbol.main], symbol]
            
        self.symbol_set = set(self.symbol_list)
        
        for k,v in self.symbol_dict.items():
            if isinstance(v, list):
                self.symbol_dict[k] = sorted(v, key=lambda s: (len(s.interventions),s.name))

    def __len__(self) -> int:
        """
        Returns the number of symbols in the container.

        Returns
        -------
        int
            The number of symbols in the container.
        """
        return len(self.symbol_list)
    
    def __getitem__(self, key: Union[int, str, List[Union[int, str]]]) -> Union['Variable', List['Variable']]:
        """
        Retrieves a symbol or a list of symbols by index or name.
        
        Parameters
        ----------
        key : Union[int, str, List[Union[int, str]]]
            The index or name of the symbol(s) to retrieve. Can also be a list of indices or names.

        Returns
        -------
        Union['Variable', List['Variable']]
            A single symbol or a list of symbols from the container.

        Raises
        ------
        KeyError
            If the key is not found in the container.
        """
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
    
    def __getattr__(self, key: str) -> 'Variable':
        """
        Access a symbol by its string name.

        Parameters
        ----------
        key : str
            The name of the symbol to access.

        Returns
        -------
        'Variable'
            The symbol corresponding to the given name.

        Raises
        ------
        AttributeError
            If the symbol name is not found in the container.
        """
        if key in self.symbol_dict:
            return self.symbol_dict[key]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __repr__(self) -> str:
        """
        Returns a string representation of the container's symbol list.

        Returns
        -------
        str
            The string representation of the container's symbol list.
        """
        return repr(self.symbol_list)
    
    def __iter__(self) -> iter:
        """
        Returns an iterator over the symbol list.

        Returns
        -------
        iter
            An iterator over the symbols in the container.
        """
        return iter(self.symbol_list)
    
    def __add__(self, other: Union[List['Variable'], Set['Variable'], 'SymbolContainer']) -> Union[List['Variable'], Set['Variable']]:
        """
        Adds symbols from another container, list, or set.

        Parameters
        ----------
        other : Union[List['Variable'], Set['Variable'], SymbolContainer]
            The object to add to the container (can be a list, set, or another SymbolContainer).

        Returns
        -------
        Union[List['Variable'], Set['Variable']]
            The resulting list or set after addition.

        Raises
        ------
        TypeError
            If the operand type is not supported for addition.
        """
        if isinstance(other, list):
            return self.symbol_list + other
        if isinstance(other, set):
            # For sets, treat + as union.
            return self.symbol_set | other
        if isinstance(other, SymbolContainer):
            return self.symbol_list + other.symbol_list
        raise TypeError(f"Unsupported operand type(s) for +: 'SymbolContainer' and '{type(other)}'")
    
    def __radd__(self, other: Union[List['Variable'], Set['Variable'], 'SymbolContainer']) -> Union[List['Variable'], Set['Variable']]:
        """
        Reverse addition: reverse the order of the operands for addition.

        Parameters
        ----------
        other : Union[List['Variable'], Set['Variable'], SymbolContainer]
            The object to add to the container (can be a list, set, or another SymbolContainer).

        Returns
        -------
        Union[List['Variable'], Set['Variable']]
            The resulting list or set after addition.
        """
        if isinstance(other, list):
            return other + self.symbol_list
        if isinstance(other, set):
            return other | self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_list + self.symbol_list
        raise TypeError(f"Unsupported operand type(s) for +: '{type(other)}' and 'SymbolContainer'")

    def __sub__(self, other: Union[List['Variable'], Set['Variable'], 'SymbolContainer']) -> Set['Variable']:
        """
        Subtracts symbols from another container, list, or set.

        Parameters
        ----------
        other : Union[List['Variable'], Set['Variable'], SymbolContainer]
            The object to subtract from the container.

        Returns
        -------
        Set['Variable']
            The resulting set after subtraction.

        Raises
        ------
        TypeError
            If the operand type is not supported for subtraction.
        """
        if isinstance(other, list):
            return self.symbol_set - set(other)
        if isinstance(other, set):
            return self.symbol_set - other
        if isinstance(other, SymbolContainer):
            return self.symbol_set - other.symbol_set
        raise TypeError(f"Unsupported operand type(s) for -: 'SymbolContainer' and '{type(other)}'")

    def __rsub__(self, other: Union[List['Variable'], Set['Variable'], 'SymbolContainer']) -> Set['Variable']:
        """
        Reverse subtraction: subtracts the container's symbols from the other.

        Parameters
        ----------
        other : Union[List['Variable'], Set['Variable'], SymbolContainer]
            The object to subtract from the container.

        Returns
        -------
        Set['Variable']
            The resulting set after subtraction.
        """
        if isinstance(other, list):
            return set(other) - self.symbol_set
        if isinstance(other, set):
            return other - self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set - self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for -: '{type(other)}' and 'SymbolContainer'")
    
    def __and__(self, other: Union[Set['Variable'], 'SymbolContainer']) -> Set['Variable']:
        """
        Computes the intersection with another container, list, or set.

        Parameters
        ----------
        other : Union[Set['Variable'], SymbolContainer]
            The object to intersect with the container.

        Returns
        -------
        Set['Variable']
            The resulting set after intersection.

        Raises
        ------
        TypeError
            If the operand type is not supported for intersection.
        """
        if isinstance(other, set):
            return self.symbol_set & other
        if isinstance(other, SymbolContainer):
            return self.symbol_set & other.symbol_set
        raise TypeError(f"Unsupported operand type(s) for &: 'SymbolContainer' and '{type(other)}'")

    def __rand__(self, other: Union[Set['Variable'], 'SymbolContainer']) -> Set['Variable']:
        """
        Reverse intersection: ensures the left-hand (other) value is handled correctly.

        Parameters
        ----------
        other : Union[Set['Variable'], SymbolContainer]
            The object to intersect with the container.

        Returns
        -------
        Set['Variable']
            The resulting set after reverse intersection.
        """
        if isinstance(other, set):
            return other & self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set & self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for &: '{type(other)}' and 'SymbolContainer'")
    
    def __or__(self, other: Union[Set['Variable'], 'SymbolContainer']) -> Set['Variable']:
        """
        Computes the union with another container, list, or set.

        Parameters
        ----------
        other : Union[Set['Variable'], SymbolContainer]
            The object to union with the container.

        Returns
        -------
        Set['Variable']
            The resulting set after union.

        Raises
        ------
        TypeError
            If the operand type is not supported for union.
        """
        if isinstance(other, set):
            return self.symbol_set | other
        if isinstance(other, SymbolContainer):
            return self.symbol_set | other.symbol_set
        raise TypeError(f"Unsupported operand type(s) for |: 'SymbolContainer' and '{type(other)}'")
    
    def __ror__(self, other: Union[Set['Variable'], 'SymbolContainer']) -> Set['Variable']:
        """
        Reverse union: when SymbolContainer is on the right.

        Parameters
        ----------
        other : Union[Set['Variable'], SymbolContainer]
            The object to union with the container.

        Returns
        -------
        Set['Variable']
            The resulting set after reverse union.
        """
        if isinstance(other, set):
            return other | self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set | self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for |: '{type(other)}' and 'SymbolContainer'")

    def __eq__(self, other: Union[Set['Variable'], List['Variable'], 'SymbolContainer']) -> bool:
        """
        Checks equality with another container, list, or set.

        Parameters
        ----------
        other : Union[Set['Variable'], List['Variable'], SymbolContainer]
            The object to compare for equality.

        Returns
        -------
        bool
            True if the objects are equal, False otherwise.
        """
        if isinstance(other, set):
            return self.symbol_set == other
        if isinstance(other, list):
            return self.symbol_list == other
        if isinstance(other, SymbolContainer):
            return self.symbol_set == other.symbol_set
        return False

    def __req__(self, other: Union[Set['Variable'], List['Variable'], 'SymbolContainer']) -> bool:
        """
        Reverse equality check (symmetric equality).

        Parameters
        ----------
        other : Union[Set['Variable'], List['Variable'], SymbolContainer]
            The object to compare for equality.

        Returns
        -------
        bool
            True if the objects are equal, False otherwise.
        """
        return self.__eq__(other)
    
    def __contains__(self, item: 'Variable') -> bool:
        """
        Checks if a symbol is contained in the container.

        Parameters
        ----------
        item : 'Variable'
            The symbol to check for containment.

        Returns
        -------
        bool
            True if the symbol is in the container, False otherwise.
        """
        return item in self.symbol_set
    
    def __hash__(self) -> int:
        """
        Returns the hash of the container (based on its symbols).

        Returns
        -------
        int
            The hash value of the container.
        """
        return hash(frozenset(self.symbol_set))
