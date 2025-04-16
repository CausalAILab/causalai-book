from abc import ABC, abstractmethod

import sympy as sp


import networkx as nx

from typing import List, Set, Dict, Tuple, Union

from causal_graph.dsep import DSeparation
from causal_graph.accessors import Accessors
from symbol_container import SymbolContainer

import causal_graph.utils as utils

from IPython.display import Latex



class Adjustments(ABC):

    @property
    @abstractmethod
    def de_graph(self):
        pass

    @property
    @abstractmethod
    def be_graph(self):
        pass

    @property
    @abstractmethod
    def v(self):
        pass

    @property
    @abstractmethod
    def syn(self):
        pass

    @property
    @abstractmethod
    def cc(self):
        pass

    
    

    def get_adjustment_backdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]],
                                      drop_z:Union[sp.Symbol, Set[sp.Symbol]]=None):
        """
        Get the conditional backdoor graph for X -> Y given the variables
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        drop_z_set = {self.syn.get(z_val, z_val) for z_val in (drop_z if isinstance(drop_z, (set, list,SymbolContainer)) else {drop_z})} if drop_z else set()
        
        trunc_pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=False)
        
        v = self.v
        de_list = [edge for edge in self.de_graph.edges if SymbolContainer(edge,self.syn) not in trunc_pcp]
        be_list = self.be_graph.edges
        
        if len(drop_z_set) > 0:
            de_list = [edge for edge in de_list if edge[0] not in drop_z_set and edge[1] not in drop_z_set]
            be_list = [edge for edge in be_list if edge[0] not in drop_z_set and edge[1] not in drop_z_set]
            v = v - drop_z_set
        
        graph = self.__class__(v,
                               de_list,
                               be_list)
        
        return graph

    def get_backdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]]):
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}

        graph = self.__class__(self.v,
                                [edge for edge in self.de_graph.edges if edge[0] not in x_set],
                                self.be_graph.edges)

        
        return graph
    
    
    
    def get_frontdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]],
                            z:Union[sp.Symbol, Set[sp.Symbol]]):
        """
        Get the frontdoor graph for X -> Y given the variables
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list,SymbolContainer)) else {z})}
        
        graph1 = self.get_adjustment_backdoor_graph(x_set,z_set)
        graph2 = self.get_adjustment_backdoor_graph(z_set,y_set)
        
        return graph1 & graph2
    
        
    

    def is_backdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               drop_z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               latex:bool=False):
        """
        Check if X is a backdoor adjustment for Y given the variables
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list,SymbolContainer)) else {z})} if z else set()
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return False
        
        
        bd_graph = self.get_adjustment_backdoor_graph(x_set,y_set,drop_z=drop_z)
        
        do_graph = self.do_x(x_set)
        
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        for path in pcp:
            for step in path[1:]:
                w_desc = set(do_graph.get_descendants(step,include_self=True))
                if (z_set & w_desc):
                    return False

        if bd_graph.is_d_separator(x_set, y_set, z_set):
            if latex:
                return self.get_backdoor_adjustment_formula(x_set,y_set,z_set)
            return True
        
        return False
    
    
    def get_backdoor_adjustment_formula(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                                        y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                                        z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                                        given:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None):
        """
        Get the backdoor adjustment formula for X -> Y given the variables
        """

        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list,SymbolContainer)) else {z})} if z else set()
        given_set = {self.syn.get(given_val, given_val) for given_val in (given if isinstance(given, (set, list,SymbolContainer)) else {given})} if given else set()
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
        

        
        if self.is_backdoor_adjustment(x_set,y_set,z_set|given_set):
            x_latex = utils.format_set(x_set)
            y_latex = utils.format_set(y_set)
            z_latex = utils.format_set(z_set)
            given_latex = utils.format_set(given_set)
            
            lhs = utils.build_conditional_set(y_latex, r'\text{do}(' + x_latex + r')', given_latex)
            
            if len(z_set) > 0:
                rhs = (
                    r'\sum_{'+ z_latex + r'} ' +
                    utils.build_conditional_set(y_latex, x_latex, z_latex, given_latex) + ' ' +
                    utils.build_conditional_set(z_latex, given_latex)
                )
            else:
                rhs = utils.build_conditional_set(y_latex, x_latex, given_latex)
                
            return Latex(f"${lhs} = {rhs}$")
            
        else:
            return None
        
        
        
    def _forbidden_set(self, z0, do_graph, pcp):
        """
        Check if there is a forbidden set between X and Y
        """
        for path in pcp:
            for step in path[1:]:
                w_desc = set(do_graph.get_descendants(step,include_self=True))
                if (z0 & w_desc):
                    return z0 & w_desc

        return set()
        
    def _exists_sep(self, x, y, z0, bd_graph):
        """
        Check if there is a separation between X and Y given Z
        """

        return bd_graph.is_d_separator(x, y, z0)
    
    def _list_seps(self, x, y, included, restricted, bd_graph,drop_z=None):
        
        z0 = set(self.get_ancestors(x | y | included, include_self=True)) & restricted
        
        if drop_z and len(drop_z) > 0:
            z0 = z0 - drop_z
        
        if self._exists_sep(x, y, z0, bd_graph):
            if (included | restricted) == included:
                return included
            else:
                w = {list(restricted - included)[-1]}
                
                res1 = self._list_seps(x, y, included | w, restricted, bd_graph, drop_z)
                res2 = self._list_seps(x, y, included, restricted - w, bd_graph,  drop_z)
                
                if res2 is not None:
                    return res2
                elif res1 is not None:
                    return res1
        
        return None

    def find_backdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               included:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               drop_z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               latex:bool=False) -> SymbolContainer:
        """
        Find a backdoor adjustment set for X -> Y
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        included_set = {self.syn.get(included_val, included_val) for included_val in (included if isinstance(included, (set, list,SymbolContainer)) else {included})} if included else set()
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list,SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        drop_z_set = {self.syn.get(drop_z_val, drop_z_val) for drop_z_val in (drop_z if isinstance(drop_z, (set, list,SymbolContainer)) else {drop_z})} if drop_z else set()
        
        included_set &= restricted_set
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
            
        bd_graph = self.get_adjustment_backdoor_graph(x_set,y_set,drop_z=drop_z)
        do_graph = self.do_x(x_set)
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        forbidden = self._forbidden_set(restricted_set, do_graph, pcp)
        
        if len(included_set & forbidden) > 0:
            return None
        
        restricted_set -= forbidden
        
        val = self._list_seps(x_set,y_set,included_set, restricted_set, bd_graph, drop_z=drop_z_set)
        
        if val:
            
            if latex:
                return self.get_backdoor_adjustment_formula(x_set,y_set,val)
            
            return SymbolContainer(val, self.syn)

        return None
    
    
        
    def find_all_backdoor_adjustments(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               included:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None) -> List[SymbolContainer]:
        
        
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        included_set = {self.syn.get(included_val, included_val) for included_val in (included if isinstance(included, (set, list,SymbolContainer)) else {included})} if included else set()        
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list,SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        included_set &= restricted_set
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
        
        bd_graph = self.get_adjustment_backdoor_graph(x_set,y_set)
        do_graph = self.do_x(x_set)
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        forbidden = self._forbidden_set(restricted_set, do_graph, pcp)
        
        if len(included_set & forbidden) > 0:
            return None
        
        
        lst =  [s for s in utils.powerset(restricted_set-forbidden) if ((sym in included for sym in s) and (self._exists_sep(x_set, y_set, s, bd_graph)))]
        
        if len(lst) > 0:
            return lst
        
        return None
        
        
        
        
    def is_frontdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               xz:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               zy:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               latex:bool=False):
        """
        Check if X is a frontdoor adjustment for Y given the variables
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list,SymbolContainer)) else {z})} if z else set()
        xz_set = {self.syn.get(z_val, z_val) for z_val in (xz if isinstance(xz, (set, list,SymbolContainer)) else {xz})} if xz else set()
        zy_set = {self.syn.get(z_val, z_val) for z_val in (zy if isinstance(zy, (set, list,SymbolContainer)) else {zy})} if zy else set()
        
        if all([
                self.is_backdoor_adjustment(x_set,z_set,xz_set),
                self.is_backdoor_adjustment(z_set,y_set,zy_set,drop_z=x_set)
                *[True for path in self.find_all_proper_causal_paths(x_set, y_set, full_path=True) if len(z_set & path) > 0],
               ]):
            
            if latex:
                return self.get_frontdoor_adjustment_formula(x_set,y_set,z_set,xz_set,zy_set)
            
            return True
        else:
            return False
        
        
        
        
    def get_frontdoor_adjustment_formula(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                                         y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                                        z:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                                        xz:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                                        zy:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None):
                                            
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list,SymbolContainer)) else {z})} if z else set()
        xz_set = {self.syn.get(z_val, z_val) for z_val in (xz if isinstance(xz, (set, list,SymbolContainer)) else {xz})} if xz else set()
        zy_set = {self.syn.get(z_val, z_val) for z_val in (zy if isinstance(zy, (set, list,SymbolContainer)) else {zy})} if zy else set()
        
        
        x_latex = utils.format_set(x_set)
        y_latex = utils.format_set(y_set)
        z_latex = utils.format_set(z_set)
        xz_latex = utils.format_set(xz_set)
        zy_latex = utils.format_set(zy_set)
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
            
        
        if self.is_frontdoor_adjustment(x_set,y_set,z_set,xz_set,zy_set):
            lhs = utils.build_conditional_set(y_latex, r'\text{do}(' + x_latex + r')')
            
            if len(z_set) > 0:
                z_sum = r'\sum_{'+ z_latex + r'} '
            else:
                z_sum = ''
                
            if len(xz_set) > 0:
                xz_sum = r'\sum_{'+ xz_latex + r'} '
            else:  
                xz_sum = ''
                
            if len(zy_set) > 0:
                zy_sum = r'\sum_{x\','+ zy_latex + r'} '
            else:
                zy_sum = r'\sum_{x\'} '
                
                
            rhs = (
                z_sum + xz_sum +
                utils.build_conditional_set(y_latex, x_latex, xz_latex) +
                (utils.build_joint_set(xz_latex) if len(xz_set) > 0 else '') +
                zy_sum + 
                utils.build_conditional_set(y_latex,"x\'",z_latex, zy_latex) +
                utils.build_joint_set("x\'",zy_latex)
            )
            
            
            return Latex(f"${lhs} = {rhs}$")
            
            
        else:
            return None
        
        
    
    
    def _list_frontdoor_z_sets(self,x,y,z, z_pot, included,restricted):
        
        
        z1 = self.find_backdoor_adjustment(x, z, included, restricted)
        z2 = self.find_backdoor_adjustment(z, y, included, restricted, drop_z=x)
        
        if all([
                z1 is not None,
                z2 is not None,
               ]):
            
            return (z, z1, z2)
        
        else:
            
            
            diff_z = list(z_pot - z)
            diff_w = list(restricted - included)
            
            if (len(diff_z) == 0 and len(diff_w) == 0):
                return None
            
            if(len(diff_z) > 0):
                new_z = {diff_z[-1]}
            else:
                new_z = set()
            if(len(diff_w) > 0):
                w = {diff_w[-1]}
            else:
                w = set()
            
            res2 = self._list_frontdoor_z_sets(x, y, z, z_pot - new_z, included, restricted - w)
            res4 = self._list_frontdoor_z_sets(x, y, z | new_z, z_pot, included, restricted - w)
            res3 = self._list_frontdoor_z_sets(x, y, z, z_pot - new_z, included | w, restricted)
            res1 = self._list_frontdoor_z_sets(x, y, z | new_z, z_pot, included | w, restricted)
            
            
            if res2 is not None:
                return res2
            if res4 is not None:
                return res4
            if res3 is not None:
                return res3
            elif res1 is not None:
                return res1
            
        return None
            
        
        

    def find_frontdoor_adjustment(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]],
                                restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                                latex:bool=False) -> Tuple[SymbolContainer]:
        """
        Find a frontdoor adjustment set for X -> Y
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list,SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        z_pot = set(step for path in pcp for step in path[1:-1])
        z = set()
        included_set = set()
        
        z_pot &= restricted_set
        
        restricted_set -= z_pot
        

        val = self._list_frontdoor_z_sets(x_set, y_set, z, z_pot, included_set, restricted_set)
        
        if val:
            
            if latex:
                return self.get_frontdoor_adjustment_formula(x_set,y_set,val[0],val[1],val[2])
            
            return tuple(SymbolContainer(val_set, self.syn) for val_set in val)
        
        return None
        
        
        
        

    def find_all_frontdoor_adjustments(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]],
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None) -> List[Tuple[SymbolContainer]]:
        """
        Find all frontdoor adjustment sets for X -> Y
        """
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list,SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        z_pot = {step for path in pcp for step in path[1:-1]}
        z = set()
        
        z_pot &= restricted_set
        
        restricted_set -= z_pot
        
        valid_sets = []
        
        for z in utils.powerset(z_pot):
              for xz in utils.powerset(restricted_set):
                  for zy in utils.powerset(restricted_set):
                    if (xz & zy): # Must be disjoint
                        continue
                      
                    if self.is_frontdoor_adjustment(x_set, y_set, z, xz, zy):
                        valid_sets.append((z, xz, zy))
                        valid_sets[-1] = tuple(SymbolContainer(val_set, self.syn) for val_set in valid_sets[-1])
                          
        if len(valid_sets) > 0:
            return valid_sets
        
        return None
        