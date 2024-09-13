import pandas as pd
import inspect

class RandomVariable:
    def __init__(self, name, fn):
        self.name = name
        specs = inspect.getfullargspec(fn)
        self.parents = specs.args
        self.fn = fn

    
        
class UnitIterator:
    def __init__(self, Pu):
        self.dist = Pu
        self.vars = list(Pu.keys())
        self.finished = False

    def __iter__(self):
        self.counter = [0] * len(self.dist)
        return self

    def __next__(self):
        if self.finished:
            raise StopIteration
        
        u = self.get_unit()
        increased = False
        for i in range(len(self.dist)-1, -1, -1):
            if (self.counter[i] + 1 < len(self.dist[self.vars[i]])):
                self.counter[i] += 1
                increased = True
                break
            else:
                self.counter[i] = 0
        if (not increased):
            self.finished = True
        return u
    
    def get_unit(self):
        unit = {}
        
        for i in range(len(self.counter)):
            var = self.vars[i]
            unit[var] = list(self.dist[var].keys())[self.counter[i]]
        return unit

class SCM:
    def __init__(self, V, Pu):
        self.V = V
        self.Pu = Pu
        self.list_parents()

    def list_parents(self):
        self.parents = {}
        for var in self.V:
            specs = inspect.getfullargspec(self.V[var])
            self.parents[var] = specs.args

    def get_probability(self, unit):
        prob = 1
        for var in unit:
            prob *= self.Pu[var][unit[var]]
        return prob

    def compute_values(self, unit, vars = None):
        if not vars:
            vars = self.V
        r = unit.copy()
        for var in vars:
            r[var] = self.compute_potential_response(var, r)
        return r
    
    def compute_potential_response(self, var, parentValues):
        args = {}
        for v in self.parents[var]:
            args[v] = parentValues[v]
        return self.V[var](**args)

    def simulate(self):
        units = UnitIterator(self.Pu)
        rows = []
        probs = []
        for u in units:
            rows.append(self.compute_values(u, self.V))
            probs.append(self.get_probability(u))
        return (rows, probs)

    def get_distribution(self, var_names = None, conditioned_on = None, marg_u = True):
        (rows, probs) = self.simulate()
        dist = pd.DataFrame(rows)
        dist['Prob'] = probs
        if not var_names:
            var_names = list(self.V)
        # var_names = list(map(lambda v: v.name, vars))
        if conditioned_on != None:
            var_names = var_names + conditioned_on
        if marg_u:
            dist = dist[var_names + ['Prob']].groupby(var_names).sum().reset_index()
        if conditioned_on != None:
            denom = dist.groupby(conditioned_on)['Prob'].transform(lambda v: v.sum())
            dist['Prob'] = dist['Prob'] / denom
            dist.sort_values(conditioned_on, inplace=True)
        return dist
    
    def intervene(self, interventions):
        Vint = self.V.copy()
        for int in interventions:
            Vint[int] = interventions[int]
        return SCM(Vint, self.Pu)

def compare_distributions(var_names, models, conditioned_on = None):
    all_dists = None
    i = 1
    for model in models:
        dist = model.get_distribution(var_names, conditioned_on = conditioned_on)
        if i == 1:
            all_dists = dist
        else:
            all_dists = all_dists.merge(dist, on = var_names, suffixes = ["" if i > 2 else "_M1", "_M" + str(i)])
        i += 1
    return all_dists
