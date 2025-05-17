from abc import ABC, abstractmethod

import sympy as sp


import networkx as nx

from typing import List, Optional, Set, Dict, Tuple, Union

from src.causal_graph.dsep import DSeparation
from src.causal_graph.accessors import Accessors
from src.return_classes import SymbolContainer

import src.causal_graph.utils as utils

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
        Construct the backdoor-adjustment graph for estimating P(Y|do(X)).

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol]]
            Effect variable(s).
        drop_z : Union[sp.Symbol, Set[sp.Symbol]], optional
            Variable(s) to remove from the graph, by default None.

        Returns
        -------
        Adjustments
            A new Adjustments instance representing the truncated graph.
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        drop_z_set = {self.syn.get(z_val, z_val) for z_val in (drop_z if isinstance(drop_z, (set, list,SymbolContainer)) else {drop_z})} if drop_z else set()
        
        trunc_pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=False)
        
        v = self.v
        de_list = [edge for edge in self.de_graph.edges if SymbolContainer(edge) not in trunc_pcp]
        be_list = self.be_graph.edges(keys=False)
        
        if len(drop_z_set) > 0:
            de_list = [edge for edge in de_list if edge[0] not in drop_z_set and edge[1] not in drop_z_set]
            be_list = [edge for edge in be_list if edge[0] not in drop_z_set and edge[1] not in drop_z_set]
            v = v - drop_z_set
        
        graph = self.__class__(v,
                               de_list,
                               be_list)
        
        return graph

    def get_backdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]]):
        """
        Construct the backdoor graph by removing edges out of X.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).

        Returns
        -------
        Adjustments
            A new Adjustments instance with edges from X removed.
        """
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}

        graph = self.__class__(self.v,
                                [edge for edge in self.de_graph.edges if edge[0] not in x_set],
                                self.be_graph.edges)

        
        return graph
    
    
    
    def get_frontdoor_graph(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]],
                            z:Union[sp.Symbol, Set[sp.Symbol]]):
        """
        Construct the frontdoor‐adjustment graph for mediators Z.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol]]
            Effect variable(s).
        z : Union[sp.Symbol, Set[sp.Symbol]]
            Mediator variable(s).

        Returns
        -------
        Adjustments
            Intersection of backdoor graphs for X→Z and Z→Y.
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
        Check whether Z satisfies the backdoor criterion for estimating P(Y|do(X)).

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Effect variable(s).
        z : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Adjustment set, by default None.
        drop_z : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Variables to exclude, by default None.
        latex : bool, optional
            If True, return LaTeX formula instead of boolean, by default False.

        Returns
        -------
        bool or Latex
            True if Z is a valid backdoor adjustment; if `latex`, return the corresponding formula.
        """
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        z_set = {self.syn.get(z_val, z_val) for z_val in (z if isinstance(z, (set, list,SymbolContainer)) else {z})} if z else set()
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return False
        
        
        bd_graph = self.get_adjustment_backdoor_graph(x_set,y_set,drop_z=drop_z)
        
        do_graph = self.do(x_set)
        
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
        Return the symbolic backdoor‐adjustment formula P(Y|do(X),…) = …

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Effect variable(s).
        z : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Adjustment set, by default None.
        given : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Additional conditioning, by default None.

        Returns
        -------
        Optional[Latex]
            LaTeX formula if adjustment holds, else None.
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
            
            lhs = utils.build_prob_exp([y_latex], [r'do(' + x_latex + r')', given_latex])
            
            if len(z_set) > 0:
                rhs = (
                    r'\sum_{'+ z_latex + r'} ' +
                    utils.build_prob_exp([y_latex], [x_latex, z_latex, given_latex]) + ' ' +
                    utils.build_prob_exp([z_latex], [given_latex])
                )
            else:
                rhs = utils.build_prob_exp([y_latex], [x_latex, given_latex])
                
            return Latex(f"${lhs} = {rhs}$")
            
        else:
            return None
        
        
        
    def _forbidden_set(self, z0, do_graph, pcp):
        """
        Identify forbidden variables that lie on causal paths.

        Parameters
        ----------
        z0 : Set[sp.Symbol]
            Candidate adjustment variables.
        do_graph : Adjustments
            Graph after do‐operation.
        pcp : list of lists
            Proper causal paths from X to Y.

        Returns
        -------
        Set[sp.Symbol]
            Variables that cannot be included in adjustment.
        """
        
        for path in pcp:
            for step in path[1:]:
                w_desc = set(do_graph.get_descendants(step,include_self=True))
                if (z0 & w_desc):
                    return z0 & w_desc

        return set()
        
    def _exists_sep(self, x, y, z0, bd_graph):
        """
        Test for d‐separation in the backdoor graph.

        Parameters
        ----------
        x : Set[sp.Symbol]
            Cause variables.
        y : Set[sp.Symbol]
            Effect variables.
        z0 : Set[sp.Symbol]
            Conditioning variables.
        bd_graph : Adjustments
            Backdoor graph.

        Returns
        -------
        bool
            True if Z0 d‐separates X and Y.
        """

        return bd_graph.is_d_separator(x, y, z0)
    
    def _list_seps(self, x, y, included, restricted, bd_graph,drop_z=None):
        
        """
        Recursively search for a valid backdoor adjustment set.

        Parameters
        ----------
        x : Set[sp.Symbol]
            Cause variables.
        y : Set[sp.Symbol]
            Effect variables.
        included : Set[sp.Symbol]
            Already included adjustment variables.
        restricted : Set[sp.Symbol]
            Remaining candidates.
        bd_graph : Adjustments
            Backdoor graph.
        drop_z : Set[sp.Symbol], optional
            Variables to exclude, by default None.

        Returns
        -------
        Optional[Set[sp.Symbol]]
            A valid adjustment set, or None.
        """
        
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
                               latex:bool=False) -> Optional[SymbolContainer]:
        """
        Find one backdoor adjustment set for X → Y.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Effect variable(s).
        included : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Variables that must be included, by default None.
        restricted : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Candidates for adjustment, by default None.
        drop_z : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Variables to exclude, by default None.
        latex : bool, optional
            If True, return formula, by default False.

        Returns
        -------
        Optional[SymbolContainer]
            An adjustment set container or None.
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
        do_graph = self.do(x_set)
        pcp = self.find_all_proper_causal_paths(x_set, y_set, full_path=True)
        
        forbidden = self._forbidden_set(restricted_set, do_graph, pcp)
        
        if len(included_set & forbidden) > 0:
            return None
        
        restricted_set -= forbidden
        
        val = self._list_seps(x_set,y_set,included_set, restricted_set, bd_graph, drop_z=drop_z_set)
        
        if val:
            
            if latex:
                return self.get_backdoor_adjustment_formula(x_set,y_set,val)
            
            return SymbolContainer(val)

        return None
    
    
        
    def find_all_backdoor_adjustments(self, x:Union[sp.Symbol, Set[sp.Symbol]],
                               y:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]],
                               included:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None,
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None) -> List[SymbolContainer]:
        """
        Enumerate all backdoor adjustment sets for X → Y.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Effect variable(s).
        included : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Variables that must be included, by default None.
        restricted : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Candidates for adjustment, by default None.

        Returns
        -------
        Optional[List[SymbolContainer]]
            A list of all valid adjustment sets, or None.
        """
        
        
        x_set = {self.syn.get(x_val, x_val) for x_val in (x if isinstance(x, (set, list,SymbolContainer)) else {x})}
        y_set = {self.syn.get(y_val, y_val) for y_val in (y if isinstance(y, (set, list,SymbolContainer)) else {y})}
        included_set = {self.syn.get(included_val, included_val) for included_val in (included if isinstance(included, (set, list,SymbolContainer)) else {included})} if included else set()        
        restricted_set = {self.syn.get(restricted_val, restricted_val) for restricted_val in (restricted if isinstance(restricted, (set, list,SymbolContainer)) else {restricted})} if restricted else set(self.v) - x_set - y_set
        
        included_set &= restricted_set
        
        if (x_set is None or len(x_set) < 1 or len(y_set) < 1 or y_set is None):
            return None
        
        bd_graph = self.get_adjustment_backdoor_graph(x_set,y_set)
        do_graph = self.do(x_set)
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
        Check whether frontdoor conditions hold for mediator Z, adjustment set X→Z, and adjustment set Z→Y.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Effect variable(s).
        z : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Mediator set, by default None.
        xz : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Adjustment set for X→Z, by default None.
        zy : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Adjustment set for Z→Y, by default None.
        latex : bool, optional
            If True, return formula, by default False.

        Returns
        -------
        bool or Latex
            True if frontdoor holds; if `latex`, return the formula.
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
        
        """
        Return symbolic frontdoor‐adjustment formula.

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]
            Effect variable(s).
        z : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Mediator set, by default None.
        xz : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Adjustment for X→Z, by default None.
        zy : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Adjustment for Z→Y, by default None.

        Returns
        -------
        Optional[Latex]
            LaTeX formula if frontdoor holds, else None.
        """
                                            
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
            lhs = utils.build_prob_exp([y_latex], [r'do(' + x_latex + r')'])
            
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
                utils.build_prob_exp([y_latex], [x_latex, xz_latex]) +
                (utils.build_prob_exp([xz_latex]) if len(xz_set) > 0 else '') +
                zy_sum + 
                utils.build_prob_exp([y_latex],["x'",z_latex, zy_latex]) +
                utils.build_prob_exp(["x'"],[zy_latex])
            )
            
            
            return Latex(f"${lhs} = {rhs}$")
            
            
        else:
            return None
        
        
    
    
    def _list_frontdoor_z_sets(self,x,y,z, z_pot, included,restricted):
        """
        Recursively search for a frontdoor triple (Z, XZ, ZY).

        Parameters
        ----------
        x : Set[sp.Symbol]
            Cause variables.
        y : Set[sp.Symbol]
            Effect variables.
        z : Set[sp.Symbol]
            Current mediator set.
        z_pot : Set[sp.Symbol]
            Potential mediators.
        included : Set[sp.Symbol]
            Already included variables.
        restricted : Set[sp.Symbol]
            Remaining candidates.

        Returns
        -------
        Optional[Tuple[Set[sp.Symbol], Set[sp.Symbol], Set[sp.Symbol]]]
            A tuple (Z, XZ, ZY) or None.
        """
        
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
        Find one valid frontdoor adjustment triple (Z, XZ, ZY).

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol]]
            Effect variable(s).
        restricted : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Candidate variables, by default None.
        latex : bool, optional
            If True, return formula, by default False.

        Returns
        -------
        Optional[Tuple[SymbolContainer, SymbolContainer, SymbolContainer]]
            A tuple of adjustment sets or None.
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
            
            return tuple(SymbolContainer(val_set) for val_set in val)
        
        return None
        
        
        
        

    def find_all_frontdoor_adjustments(self, x:Union[sp.Symbol, Set[sp.Symbol]], y:Union[sp.Symbol, Set[sp.Symbol]],
                               restricted:Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]]=None) -> List[Tuple[SymbolContainer]]:
        
        """
        Enumerate all frontdoor adjustment triples (Z, XZ, ZY).

        Parameters
        ----------
        x : Union[sp.Symbol, Set[sp.Symbol]]
            Cause variable(s).
        y : Union[sp.Symbol, Set[sp.Symbol]]
            Effect variable(s).
        restricted : Union[sp.Symbol, Set[sp.Symbol], List[sp.Symbol]], optional
            Candidate variables, by default None.

        Returns
        -------
        Optional[List[Tuple[SymbolContainer, SymbolContainer, SymbolContainer]]]
            List of all valid adjustment triples or None.
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
                        valid_sets[-1] = tuple(SymbolContainer(val_set) for val_set in valid_sets[-1])
                          
        if len(valid_sets) > 0:
            return valid_sets
        
        return None
        