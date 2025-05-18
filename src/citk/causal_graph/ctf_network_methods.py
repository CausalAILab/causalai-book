from abc import ABC, abstractmethod
from typing import List, Set, Union

from src.sympy_classes import Variable, Pr

from src.return_classes import SymbolContainer
from src.sympy_classes.summation import Summation
import sympy as sp


import networkx as nx



class CtfNetworkMethods(ABC):

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
    
    

       

                    
        
        
        
    
    
    def build_TWN(self,interventions: Set[Variable]):
        
        """
        Constructs a Twin Network (TWN) for a set of interventions.

        The Twin Network duplicates variables to simulate a counterfactual world where
        a given set of interventions is applied. It includes the original and intervened
        variables, connecting them via both directed and bidirected edges.

        Parameters
        ----------
        interventions : Set[Variable]
            A set of variables that are intervened upon.

        Returns
        -------
        CtfNetworkMethods
            An instance of the class with the constructed twin network graph.
        """
        
        # Leaves in self-interventions
        
        v_out = set(self.v)
        de_edges = [*self.de_graph.edges]
        be_edges = [*self.be_graph.edges(keys=False)]
        
        interventions = interventions if isinstance(interventions, (set,list)) else {interventions}
        
        groups = {v.main:{v} for v in self.v}
        
        g_do = self.do(interventions)
        
        do_v = g_do.v
        do_de_edges = g_do.de_graph.edges
        

        map = {}
        
        for v in do_v:
            excluded_v = self.apply_exclusion_var(v)
            map[v] = excluded_v
            v_out.add(excluded_v)
            if Variable(excluded_v.main) not in excluded_v.interventions.keys(): # Not its own intervention
                groups[v.main].add(excluded_v)
                
        for e in do_de_edges:
            de_edges.append((map[e[0]], map[e[1]]))
            
        
        # This must come before the next step
        to_add = set()
        for e in be_edges:
            for elem in groups[e[0].main]:
                if elem != e[0]:
                    to_add.add((elem, e[1]))
                    to_add.add((e[0], elem))
            for elem in groups[e[1].main]:
                if elem != e[1]:
                    to_add.add((e[0], elem))
                    to_add.add((elem, e[1]))
                
        be_edges.extend(list(to_add))
            
            
        for g in groups:
            if len(groups[g]) > 1:
                items = list(groups[g])
                for i in range(len(items)):
                    for j in range(i+1, len(items)):
                        be_edges.append((items[i], items[j]))
                            
        
                
        return self.__class__(
            v=v_out,
            directed_edges=de_edges,
            bidirected_edges=be_edges,
        )
            
            
        
        
    
    
    def build_MWN(self, *interventions: Set[Variable]):
        
        """
        Constructs a Multi-World Network (MWN) from a sequence of interventions.

        This method builds a graph that includes variables from multiple 
        counterfactual worlds, each corresponding to a different intervention set.
        Self-interventions are dropped.

        Parameters
        ----------
        *interventions : Set[Variable]
            One or more sets of interventions representing different worlds.

        Returns
        -------
        CtfNetworkMethods
            An instance of the class with the constructed multi-world network graph.
        """
        
        # Drops self-interventions
    
        interventions_list = [i if isinstance(i, (set,list)) else {i} \
                             for i in interventions]
        
        v_out = set(self.v)
        de_edges = [*self.de_graph.edges]
        be_edges = [*self.be_graph.edges(keys=False)]
        
        groups = {v.main:{v} for v in self.v}
        
        for inter in interventions_list:
            
            map = {}
            
            g_do = self.do(inter)
            do_de_edges = g_do.de_graph.edges
            
            do_v = g_do.v
            
            for v in do_v:
                excluded_v = self.apply_exclusion_var(v)
                if Variable(excluded_v.main) not in excluded_v.interventions.keys(): # Not its own intervention
                    map[v] = excluded_v
                    v_out.add(excluded_v)
                    groups[v.main].add(excluded_v)


                    
            for e in do_de_edges:
                if e[0] in map and e[1] in map: # Ignores dropped variables; i.e., self-interventions
                    de_edges.append((map[e[0]], map[e[1]]))
                
                
        to_add = set()
        for e in be_edges:
            for elem in groups[e[0].main]:
                if elem != e[0]:
                    to_add.add((elem, e[1]))
                    to_add.add((e[0], elem))
            for elem in groups[e[1].main]:
                if elem != e[1]:
                    to_add.add((e[0], elem))
                    to_add.add((elem, e[1]))
                
        be_edges.extend(list(to_add)) 
        
                
                
        for g in groups:
            if len(groups[g]) > 1:
                items = list(groups[g])
                for i in range(len(items)):
                    for j in range(i+1, len(items)):
                        be_edges.append((items[i], items[j]))
                        

        return self.__class__(
            v=v_out,
            directed_edges=de_edges,
            bidirected_edges=be_edges,
        )
        
    
    def build_AMWN(self, counterfactuals: Set[Variable]):
        
        """
        Constructs an Ancestral Multi-World Network (AMWN) for a set of counterfactuals.

        The AMWN contains only the counterfactual variables and their ancestors
        in the graph. Edges are added based on the directed and bidirected relationships
        among the relevant variables after applying necessary exclusions.

        Parameters
        ----------
        counterfactuals : Set[Variable]
            A set of counterfactual variables to anchor the network construction.

        Returns
        -------
        CtfNetworkMethods
            An instance of the class with the constructed ancestral multi-world network graph.
        """
        
        # Drops self-interventions
        
        ctfs = counterfactuals if isinstance(counterfactuals, (set,list)) else {counterfactuals}
        
        anc = self.get_ctf_ancestors(ctfs)
        de_edges = []
        be_edges = []
        
        v = anc
        
        visited = set()
        
        for v_i in v:
            visited.add(v_i)
            pa = self.get_parents(v_i)
            neighb = self.get_neighbors(v_i) - visited
            for p in pa:
                excluded_p = self.apply_exclusion_var(p)
                if excluded_p in v:
                    de_edges.append((excluded_p, v_i))
            for n in neighb:
                excluded_n = self.apply_exclusion_var(n)
                excluded_n = Variable(excluded_n.main) if Variable(excluded_n.main) == ([None] + list(excluded_n.interventions.keys()))[-1] else excluded_n # Self-intervention
                if excluded_n in v:
                    be_edges.append((excluded_n, v_i))
                    
        
        for i, v_i in enumerate(v):
            for j, v_j in enumerate(v[i+1:]):
                if v_i.main == v_j.main:
                    be_edges.append((v_i, v_j))
                    
        return self.__class__(
            v=v,
            directed_edges=de_edges,
            bidirected_edges=be_edges,
        )
        
        
       
        
        
        