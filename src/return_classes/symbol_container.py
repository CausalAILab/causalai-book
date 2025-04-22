

from typing import List, Dict, Set, Union
import sympy as sp

class SymbolContainer:
    """
    A container for managing a collection of sympy.Symbols with various operations.

    Attributes
    ----------
    symbol_list : List[sp.Symbol]
        A list of sympy.Symbols stored in the container.
    symbol_dict : Dict[str, sp.Symbol]
        A dictionary mapping string representations of symbols to their corresponding sympy.Symbols.
    symbol_set : Set[sp.Symbol]
        A set of sympy.Symbols stored in the container for efficient set operations.

    Methods
    -------
    __len__() -> int
        Returns the number of symbols in the container.
    __getitem__(key) -> Union[sp.Symbol, List[sp.Symbol]]
        Retrieves a symbol or a list of symbols by index or name.
    __getattr__(key) -> sp.Symbol
        Access a symbol by its string name.
    __repr__() -> str
        Returns a string representation of the container's symbol list.
    __iter__() -> iter
        Returns an iterator over the symbol list.
    __add__(other) -> Union[List[sp.Symbol], Set[sp.Symbol]]
        Adds symbols from another container, list, or set.
    __radd__(other) -> Union[List[sp.Symbol], Set[sp.Symbol]]
        Reverse add operation for lists, sets, or containers.
    __sub__(other) -> Set[sp.Symbol]
        Subtracts symbols from another container, list, or set.
    __rsub__(other) -> Set[sp.Symbol]
        Reverse subtraction operation.
    __and__(other) -> Set[sp.Symbol]
        Computes the intersection with another container, list, or set.
    __rand__(other) -> Set[sp.Symbol]
        Reverse intersection operation for containers and sets.
    __or__(other) -> Set[sp.Symbol]
        Computes the union with another container, list, or set.
    __ror__(other) -> Set[sp.Symbol]
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

    def __init__(self, symbols: List[sp.Symbol] = None, syn: Dict[sp.Symbol, sp.Symbol] = None):
        """
        Initializes the SymbolContainer with a list of symbols and an optional dictionary of synonym mappings.
        
        Parameters
        ----------
        symbols : List[sp.Symbol], optional
            A list of sympy.Symbols to initialize the container (default is an empty list).
        syn : Dict[sp.Symbol, sp.Symbol], optional
            A dictionary mapping symbols to their synonyms (default is an empty dictionary).
        """
        if symbols is None:
            symbols = []
        if syn is None:
            syn = {}
        
        self.symbol_list = list(symbols)
        self.symbol_dict = {str(s): s for s in symbols} | {str(k): v for k, v in syn.items()}
        self.symbol_set = set(self.symbol_list)

    def __len__(self) -> int:
        """
        Returns the number of symbols in the container.

        Returns
        -------
        int
            The number of symbols in the container.
        """
        return len(self.symbol_list)
    
    def __getitem__(self, key: Union[int, str, List[Union[int, str]]]) -> Union[sp.Symbol, List[sp.Symbol]]:
        """
        Retrieves a symbol or a list of symbols by index or name.
        
        Parameters
        ----------
        key : Union[int, str, List[Union[int, str]]]
            The index or name of the symbol(s) to retrieve. Can also be a list of indices or names.

        Returns
        -------
        Union[sp.Symbol, List[sp.Symbol]]
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
    
    def __getattr__(self, key: str) -> sp.Symbol:
        """
        Access a symbol by its string name.

        Parameters
        ----------
        key : str
            The name of the symbol to access.

        Returns
        -------
        sp.Symbol
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
    
    def __add__(self, other: Union[List[sp.Symbol], Set[sp.Symbol], 'SymbolContainer']) -> Union[List[sp.Symbol], Set[sp.Symbol]]:
        """
        Adds symbols from another container, list, or set.

        Parameters
        ----------
        other : Union[List[sp.Symbol], Set[sp.Symbol], SymbolContainer]
            The object to add to the container (can be a list, set, or another SymbolContainer).

        Returns
        -------
        Union[List[sp.Symbol], Set[sp.Symbol]]
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
    
    def __radd__(self, other: Union[List[sp.Symbol], Set[sp.Symbol], 'SymbolContainer']) -> Union[List[sp.Symbol], Set[sp.Symbol]]:
        """
        Reverse addition: reverse the order of the operands for addition.

        Parameters
        ----------
        other : Union[List[sp.Symbol], Set[sp.Symbol], SymbolContainer]
            The object to add to the container (can be a list, set, or another SymbolContainer).

        Returns
        -------
        Union[List[sp.Symbol], Set[sp.Symbol]]
            The resulting list or set after addition.
        """
        if isinstance(other, list):
            return other + self.symbol_list
        if isinstance(other, set):
            return other | self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_list + self.symbol_list
        raise TypeError(f"Unsupported operand type(s) for +: '{type(other)}' and 'SymbolContainer'")

    def __sub__(self, other: Union[List[sp.Symbol], Set[sp.Symbol], 'SymbolContainer']) -> Set[sp.Symbol]:
        """
        Subtracts symbols from another container, list, or set.

        Parameters
        ----------
        other : Union[List[sp.Symbol], Set[sp.Symbol], SymbolContainer]
            The object to subtract from the container.

        Returns
        -------
        Set[sp.Symbol]
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

    def __rsub__(self, other: Union[List[sp.Symbol], Set[sp.Symbol], 'SymbolContainer']) -> Set[sp.Symbol]:
        """
        Reverse subtraction: subtracts the container's symbols from the other.

        Parameters
        ----------
        other : Union[List[sp.Symbol], Set[sp.Symbol], SymbolContainer]
            The object to subtract from the container.

        Returns
        -------
        Set[sp.Symbol]
            The resulting set after subtraction.
        """
        if isinstance(other, list):
            return set(other) - self.symbol_set
        if isinstance(other, set):
            return other - self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set - self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for -: '{type(other)}' and 'SymbolContainer'")
    
    def __and__(self, other: Union[Set[sp.Symbol], 'SymbolContainer']) -> Set[sp.Symbol]:
        """
        Computes the intersection with another container, list, or set.

        Parameters
        ----------
        other : Union[Set[sp.Symbol], SymbolContainer]
            The object to intersect with the container.

        Returns
        -------
        Set[sp.Symbol]
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

    def __rand__(self, other: Union[Set[sp.Symbol], 'SymbolContainer']) -> Set[sp.Symbol]:
        """
        Reverse intersection: ensures the left-hand (other) value is handled correctly.

        Parameters
        ----------
        other : Union[Set[sp.Symbol], SymbolContainer]
            The object to intersect with the container.

        Returns
        -------
        Set[sp.Symbol]
            The resulting set after reverse intersection.
        """
        if isinstance(other, set):
            return other & self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set & self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for &: '{type(other)}' and 'SymbolContainer'")
    
    def __or__(self, other: Union[Set[sp.Symbol], 'SymbolContainer']) -> Set[sp.Symbol]:
        """
        Computes the union with another container, list, or set.

        Parameters
        ----------
        other : Union[Set[sp.Symbol], SymbolContainer]
            The object to union with the container.

        Returns
        -------
        Set[sp.Symbol]
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
    
    def __ror__(self, other: Union[Set[sp.Symbol], 'SymbolContainer']) -> Set[sp.Symbol]:
        """
        Reverse union: when SymbolContainer is on the right.

        Parameters
        ----------
        other : Union[Set[sp.Symbol], SymbolContainer]
            The object to union with the container.

        Returns
        -------
        Set[sp.Symbol]
            The resulting set after reverse union.
        """
        if isinstance(other, set):
            return other | self.symbol_set
        if isinstance(other, SymbolContainer):
            return other.symbol_set | self.symbol_set
        raise TypeError(f"Unsupported operand type(s) for |: '{type(other)}' and 'SymbolContainer'")

    def __eq__(self, other: Union[Set[sp.Symbol], List[sp.Symbol], 'SymbolContainer']) -> bool:
        """
        Checks equality with another container, list, or set.

        Parameters
        ----------
        other : Union[Set[sp.Symbol], List[sp.Symbol], SymbolContainer]
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

    def __req__(self, other: Union[Set[sp.Symbol], List[sp.Symbol], 'SymbolContainer']) -> bool:
        """
        Reverse equality check (symmetric equality).

        Parameters
        ----------
        other : Union[Set[sp.Symbol], List[sp.Symbol], SymbolContainer]
            The object to compare for equality.

        Returns
        -------
        bool
            True if the objects are equal, False otherwise.
        """
        return self.__eq__(other)
    
    def __contains__(self, item: sp.Symbol) -> bool:
        """
        Checks if a symbol is contained in the container.

        Parameters
        ----------
        item : sp.Symbol
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
