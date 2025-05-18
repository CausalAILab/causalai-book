from typing import Dict, Set, Union
import sympy as sp



def variables(names: str):
    """
    Create a list of Variable instances from a string of variable names.
    
    Parameters
    ----------
    names : str
        A string containing variable names separated by commas.
    
    Returns
    -------
    List[Variable]
        A list of Variable instances.
    """
    
    tup = [Variable(name.strip()) for name in names.split(" ")]
    
    if len(tup) == 1:
        return tup[0]
    else:
        return tup


class Variable(sp.Symbol):
    
    def __new__(cls, main: 'str', interventions:Union[Dict['Variable',Union[int,str,'Variable',None]],Set['Variable']] = None):
        """
        Create a new Variable instance.
        
        Parameters
        ----------
        symbol : str
            The symbol name.
        main : str
            The main name of the variable.
        interventions : Dict[Variable, Variable], optional
            A dictionary of interventions associated with the variable, by default None.
        
        Returns
        -------
        Variable
            A new instance of the Variable class.
        """
        interventions = interventions or {}
        
        if isinstance(interventions, dict):
            interventions = {k:v for k,v in interventions.items()}
        
        if isinstance(interventions, (set,list)):
            interventions = {
                            **{k:None for k in list(interventions) if k.main==str(k.name)},
                            **{Variable(k.main):k for k in list(interventions) if k.main!=str(k.name)}
                            }
        
        if interventions:
            subscript = ",".join(f"{str(k)}={str(interventions[k])}" if interventions[k] is not None else f"{k}" for k in interventions.keys())
            symbol = f"{main}_{{{subscript}}}"
        else:
            symbol = f"{main}"
            
            
        obj = super().__new__(cls, symbol)
        obj.main = main
        obj.interventions = interventions
        
        return obj
            
            
            
    def update_interventions(self, interventions:Union[Dict['Variable',Union[int,str,'Variable',None]],Set['Variable']] ):
        
        """
        Update the interventions of the variable.
        
        Parameters
        ----------
        interventions : Dict[str, Union[int, str, Variable]]
            A dictionary of new interventions to be added to the variable.
        
        Returns
        -------
        None
        """
        
        if isinstance(interventions, dict):
            interventions = {k:v for k,v in interventions.items()}
        
        if isinstance(interventions, (set,list)):
            interventions = {
                            **{k:None for k in list(interventions) if k.main==str(k.name)},
                            **{Variable(k.main):k for k in list(interventions) if k.main!=str(k.name)}
                            }
        
        updated_interventions = self.interventions.copy()
        updated_interventions.update(interventions)
        
        return Variable(self.main, updated_interventions)
    
    
    def remove_interventions(self, interventions:Set['Variable']):
        """
        Remove the specified intervention from the variable.
        
        Parameters
        ----------
        intervention : Dict[str, Union[int, str, Variable]]
            A dictionary of interventions to be removed from the variable.
        
        Returns
        -------
        None
        """
        
        updated_interventions = self.interventions.copy()
        
        for key in interventions:
            if key in updated_interventions:
                del updated_interventions[key]
                
        return Variable(self.main, updated_interventions)
    
        
        
    def __repr__(self):
        return self.name
        
        
    def _sympystr(self, printer):
        return self.name
    
    
    def __hash__(self):
        return super().__hash__()
        
        
    