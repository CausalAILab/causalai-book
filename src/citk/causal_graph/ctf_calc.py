from abc import ABC, abstractmethod
from typing import Dict, List, Set, Union

from src.sympy_classes import Variable, Pr

from src.return_classes import SymbolContainer
from src.sympy_classes.summation import Summation
import sympy as sp


import networkx as nx



class DoCalc(ABC):

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
    
    
    
    def apply_r1(self, pr:Pr, target_var: Union[Variable,Set[Variable], List[Variable]],
                        intervention_var: Union[Variable, Set[Variable], List[Variable]],
                        method:str = 'remove'):
        """
        Apply Rule 1 (Consistency) of the ctf-calculus to the given probability expression.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable]]
            The variables whose consistency should be evaluated.
        intervention_var : Union[Variable, Set[Variable], List[Variable]]
            The variables representing the interventions to apply or remove.
        method : str, default='remove'
            Whether to remove or add the intervention ('remove' or 'add').

        Returns
        -------
        Pr
            A modified probability expression with the consistency condition applied.
        """
        
        return self.apply_consistency(pr, target_var, intervention_var, method)
    
    def apply_r2(self, pr: Pr, target_var: Union[Variable, Set[Variable], List[Variable], Dict[Variable,int]] = None,
                           method: str = 'remove'):
        
        """
        Apply Rule 2 (Independence) of the ctf-calculus to the given probability expression.
        If target_var is None, the method will attempt to remove all variables in the condition set.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable], Dict[Variable, int]], optional
            Variables found in the condition that are conditionally independent from all variables in the event.
        method : str, default='remove'
            Whether to remove or add the variables from the condition set ('remove' or 'add').

        Returns
        -------
        Pr
            A modified probability expression with the independence condition applied.
        """
        
        return self.apply_independence(pr, target_var, method)
        
    
    def apply_r3(self, pr:Pr, target_var: Union[Variable,Set[Variable], List[Variable]],
                        intervention_var: Union[Variable, Set[Variable], List[Variable], Dict[Variable,int]] = None,
                        method:str = 'remove'):

        """
        Apply Rule 3 (Exclusion) of the ctf-calculus to the given probability expression.
        If intervention_var is None, the method will attempt to remove all interventions from the target.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable]]
            The variables to which exclusion is applied.
        intervention_var : Union[Variable, Set[Variable], List[Variable], Dict[Variable, int]], optional
            Interventions to remove or add for exclusion testing.
        method : str, default='remove'
            Whether to remove or add the intervention ('remove' or 'add').

        Returns
        -------
        Pr
            A modified probability expression with the exclusion condition applied.
        """
        
        return self.apply_exclusion(pr, target_var, intervention_var, method)
    
    
    def apply_independence(self, pr: Pr, target_var: Union[Variable, Set[Variable], List[Variable], Dict[Variable,int]] = None,
                           method: str = 'remove'):
        """
        Apply the d-separation-based independence condition on the AMWN to remove or add variables
        from the conditional set of the probability expression.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable], Dict[Variable, int]], optional
            Target variables to test independence against.
        method : str, default='remove'
            Whether to remove or add the target variables to the condition ('remove' or 'add').

        Returns
        -------
        Pr
            A modified probability expression with the updated conditional set.
        """
        
        
        assert method in ['remove', 'add'], "Method must be either 'remove' or 'add'"
        
        main = pr.get_event()
        given = pr.get_condition()
        do_obj = pr.get_action()
        
        
        assert all([main is not None, given is not None]), "Main and given variables must be provided."
            
        
        if target_var is not None:
            if isinstance(target_var, dict):
                target_var = {self.syn.get(n,n):v for n,v in target_var.items()}
            else:
                target_var = set(target_var) if isinstance(target_var, (set, list)) else {target_var}
                target_var = {self.syn.get(n, n):None for n in target_var}
        else:
            if method =='add':
                raise ValueError("target_var must be provided when method is 'add'")
            else:
                target_var = {var:val for var,val in given.items()}    
            
            
        if do_obj is not None:
            self.do(do_obj)
            main = {k.update_interventions(do_obj):v for k,v in main.items()}
            if given is not None:
                given = {k.update_interventions(do_obj):v for k,v in given.items()}
            if target_var is not None:
                target_var = {k.update_interventions(do_obj):v for k,v in target_var.items()}
            

        w = {k:v for k,v in given.items() if k not in target_var}
        
        amwn = self.build_AMWN(set(main.keys()) | set(given.keys()) | set(target_var.keys()))
        
        new_given = given
        
        if amwn.is_d_separator(x=set(main.keys()), y = set(target_var.keys()), given = set(w.keys())):
            if method == 'remove':
                new_given = {k:v for k,v in given.items() if k not in target_var}
            if method == 'add':
                new_given.update(target_var)
        
        
            
        return Pr(
            main,
            given=new_given,
            do=None
        )
            
            
            
            
            
        
        
    
    def apply_consistency(self, pr: Pr, target_var: Union[Variable, Set[Variable], List[Variable]],
                          intervention_var: Union[Variable, Set[Variable], List[Variable]],
                          method: str = 'remove'):
        """
        Apply the consistency condition by aligning counterfactual interventions with observed settings.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable]]
            Target variables to which consistency should be applied.
        intervention_var : Union[Variable, Set[Variable], List[Variable]]
            Intervened variables whose values are assumed consistent.
        method : str, default='remove'
            Whether to remove or add the interventions ('remove' or 'add').

        Returns
        -------
        Pr
            A modified probability expression with consistent counterfactual interventions.
        """
        
        assert method in ['remove', 'add'], "Method must be either 'remove' or 'add'"
    
        target_var = set(target_var) if isinstance(target_var, (set, list)) else {target_var}
        target_var = {self.syn.get(n, n) for n in target_var}
        
        if intervention_var is None:
            if method == 'add':
                raise ValueError("intervention_var must be provided when method is 'add'")
            if method == 'remove':
                intervention_var = {key:val for var in target_var for key,val in var.interventions.items()}
        else:
            if isinstance(intervention_var, dict):
                intervention_var = {n:v for n,v in intervention_var.items()}
            else:
                intervention_var = set(intervention_var) if isinstance(intervention_var, (set, list)) else {intervention_var}
                intervention_var = {n:None for n in intervention_var}
            
        
        main_obj = pr.get_event()
        given_obj = pr.get_condition()
        do_obj = pr.get_action()
        
        assert all(n in main_obj for n in target_var), f"Target with value {target_var} must be a subset of event variables: {main_obj.keys()}"
        
        assert len(intervention_var) == 1 if any(len(iv.interventions) > 0 for iv in intervention_var) else True, "A counterfactual variable passed as an intervention_var must be by itself."
        
        if do_obj is not None:
            self.do(do_obj)
            main_obj = {k.update_interventions(do_obj):v for k,v in main_obj.items()}
            if given_obj is not None:
                given_obj = {k.update_interventions(do_obj):v for k,v in given_obj.items()}
            if target_var is not None:
                target_var = {k.update_interventions(do_obj) for k in target_var}
    
        main_vars = {}
        og_to_variation = {k:k for k in main_obj.keys()}
        
        consideration_vars = set((k,v) for k,v in main_obj.items() if k not in target_var)
        consideration_dict = {k:v for k,v in main_obj.items() if k not in target_var}
            
        for var,setting in main_obj.items():
            

            if var not in target_var:
                continue
            
            target_int = var.interventions # Intervention dict for variables structures ctfs like x : x_w
            
            ctf = list(intervention_var.keys())[0] # Assumption only one intervention var if ctf
            
            if len(ctf.interventions) > 0: # Nested counterfactual
                
                if ctf in consideration_dict.keys():
                
                    if method == 'remove':
                        og_to_variation[var] = og_to_variation[var].update_interventions({Variable(ctf.main):consideration_dict[ctf]})
                    elif method == 'add':
                        if consideration_dict[ctf] == target_int[Variable(ctf.main)]: # E.g. Failure: y_{x=0} and x_{w=w} = 1
                            og_to_variation[var] = og_to_variation[var].update_interventions({Variable(ctf.main):ctf})
                
            else:
                
                T = {k:v for k,v in target_int.items() if k not in intervention_var}
                
                intervention_var_T = set((k.update_interventions(T), consideration_dict.get(k.update_interventions(T),v) if v is None else v) for k,v in intervention_var.items())
                
                iv_to_ivT = {k:k.update_interventions(T) for k in intervention_var.keys()}
                
                if intervention_var_T & consideration_vars == intervention_var_T:
                    if method == 'remove':
                        og_to_variation[var] = og_to_variation[var].remove_interventions(intervention_var)
                    elif method == 'add':
                        og_to_variation[var] = og_to_variation[var].update_interventions({k:consideration_dict[iv_to_ivT[k]] for k in intervention_var})
                    
                    
                    
        for var, setting in main_obj.items():
            main_vars[og_to_variation[var]] = setting
            
            # Eagerly generate counterfactual graphs for any new interventions
            self.do(og_to_variation[var].interventions)
                    
                    
            
        return Pr(main_vars, given=given_obj, do=None)
            
            
                        
                
    def apply_ctf_unnest(self, pr: Pr, target_var: Union[Variable, Set[Variable], List[Variable]] = None):
        """
        Unnests nested counterfactual variables by introducing summation over latent assignments.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable]], optional
            The counterfactual variables to unnest.

        Returns
        -------
        Summation
            A symbolic summation over unnested counterfactual variables.
        """
        
        if target_var is not None:
            target_var = set(target_var) if isinstance(target_var, (set, list)) else {target_var}
            target_var = {self.syn.get(n, n) for n in target_var}
        
        
        main_obj = pr.get_event()
        cond_obj = pr.get_condition()
        do_obj = pr.get_action()
        
        if do_obj is not None:
            self.do(do_obj)
            main_obj = {k.update_interventions(do_obj):v for k,v in main_obj.items()}
            if cond_obj is not None:
                cond_obj = {k.update_interventions(do_obj):v for k,v in cond_obj.items()}
            if target_var is not None:
                target_var = {k.update_interventions(do_obj) for k in target_var}
            
                
            
    
        cond = True

        index_vars = []
        y = {k:v for k,v in main_obj.items() if (target_var is None or k in target_var)}
        new_y = {k:v for k,v in main_obj.items() if (target_var is not None and k not in target_var)}
            
        while cond:
            search = list(y.items())
            
            cond = False
            
            to_delete = []
            
            for var,setting in search:
                
                inters = var.interventions
            
                updates = {}
                
                
                for k,v in inters.items():
                    if isinstance(v, Variable):
                        y[v] = Variable(v.main)
                        updates[k] = Variable(v.main)
                        index_vars.append(Variable(v.main))
                        cond |= True
                       
                to_delete.append(var)
                new_var = var.update_interventions(updates)
                new_y[new_var] = setting
                
            for d in to_delete:
                del y[d]
                
        for var,setting in new_y.items():
            self.do(var.interventions)

                
        return Summation(Pr(new_y, given=cond_obj, do=None), *index_vars)
                        
    
    
    
    
    def apply_exclusion_var(self, var: Variable):
        
        if var.interventions is None:
            return var
        
        if var not in self._ctf_graphs:
            raise ValueError(f"Node {var} not found in submodels with keys: {self._ctf_graphs.keys()}.")
            
        do_graph = self._ctf_graphs[var]
        
        interventions = var.interventions.keys()
        
        anc = do_graph.get_ancestors(var,include_self=True)
        
        z = set([a.main for a in anc]) & set([inter.main for inter in interventions])
        
        excluded_var = var.remove_interventions([i for i in interventions if i.main not in z])
        
        self.do(list(excluded_var.interventions))
            
            
        return excluded_var
                        
        
        
        
    def apply_exclusion(self, pr:Pr, target_var: Union[Variable,Set[Variable], List[Variable]],
                        intervention_var: Union[Variable, Set[Variable], List[Variable], Dict[Variable,int]]=None,
                        method:str = 'remove'):
        
        """
        Applies the exclusion condition to target variables by modifying interventions
        based on their relevance in the graph structure.

        Parameters
        ----------
        pr : Pr
            The probability expression to modify.
        target_var : Union[Variable, Set[Variable], List[Variable]]
            The target variables to which the exclusion condition is applied.
        intervention_var : Union[Variable, Set[Variable], List[Variable], Dict[Variable, int]], optional
            Interventions to evaluate for exclusion.
        method : str, default='remove'
            Whether to remove or add the interventions ('remove' or 'add').

        Returns
        -------
        Pr
            A modified probability expression with exclusion logic applied to target variables.
        """
        
        assert method in ['remove', 'add'], "Method must be either 'remove' or 'add'"
        

        target_var = set(target_var) if isinstance(target_var, (set, list)) else {target_var}
        target_var = {self.syn.get(n, n) for n in target_var}
            

        if intervention_var is None:
            if method == 'add':
                raise ValueError("intervention_var must be provided when method is 'add'")
            if method == 'remove':
                intervention_var = {key:val for var in target_var for key,val in var.interventions.items()}
        else:
            if isinstance(intervention_var, dict):
                intervention_var = {Variable(n.main):v for n,v in intervention_var.items()}
            else:
                intervention_var = set(intervention_var) if isinstance(intervention_var, (set, list)) else {intervention_var}
                intervention_var = {Variable(n.main):None for n in intervention_var}

        
        
        main = pr.get_event()
        given = pr.get_condition()
        do_obj = pr.get_action()
        
        assert all(t in main for t in target_var), f"Target with value {target_var} must be a subset of event variables: {main.keys()}"
        
        if do_obj is not None:
            self.do(do_obj)
            main = {k.update_interventions(do_obj):v for k,v in main.items()}
            if given is not None:
                given = {k.update_interventions(do_obj):v for k,v in given.items()}
            if target_var is not None:
                target_var = {k.update_interventions(do_obj) for k in target_var}
        
        excluded_y = {}
        
        for var,setting in main.items():
            if var not in target_var:
                excluded_y[var] = setting
                continue
            
            interventions = set(var.interventions.keys()) - set(intervention_var.keys())
            
            do_graph = self.do(interventions)
            
            anc = do_graph.get_ancestors(var,include_self=True)
            
            z = set([a.main for a in anc]) & set([var.main for var in intervention_var.keys()])
            
            if z != set():
                # Failed test
                excluded_y[var] = setting
                continue
            
            if method == 'remove':
                excluded_y[var.remove_interventions(intervention_var)] = setting
            if method == 'add':
                excluded_y[var.update_interventions(intervention_var)] = setting
        
        # Eagerly generate counterfactual graphs for intervention sets on excluded_y
        for y in excluded_y:
            self.do(y.interventions)
            
            
        return Pr(
            excluded_y,
            given=pr.get_condition(),
            do=None
        )
            
            



