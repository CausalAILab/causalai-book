from collections import deque

class CausalDiagram:

    def __init__(self, V, directed_edges=[], bidirected_edges=[]):
        
        self.de = directed_edges
        self.be = bidirected_edges
        self.v = list(V)

        self.pa = {v: set() for v in self.v}
        self.ch = {v: set() for v in self.v}
        self._get_parents_children()

        self.ne = {v: set() for v in self.v}
        self._get_neighbors()

        self._sort()

        self.bi = set(map(tuple, map(sorted, bidirected_edges)))


    def _get_parents_children(self):
        # Get parents and children
        for x, y in self.de:
            self.pa[y].add(x)
            self.ch[x].add(y)

    def _get_neighbors(self):
        # Get neighbors
        for u, v in self.be:
            self.ne[u].add(v)
            self.ne[v].add(u)

    def _sort(self):
        # Topological sort using Kahn's algorithm
        in_degree = {v: len(self.pa[v]) for v in self.v}
        q = deque([v for v in self.v if in_degree[v] == 0])

        sorted_v = []
        while q:
            v = q.popleft()
            sorted_v.append(v)
            for ch in self.ch[v]:
                in_degree[ch] -= 1
                if in_degree[ch] == 0:
                    q.append(ch)
        
        if len(sorted_v) != len(self.v):
            raise ValueError("Graph contains a cycle")
        else:
            self.v = sorted_v

    def bayesian_factorization(self):

        if self.be:
            raise ValueError("Graph is not Markovian")
        
        factorization = "P(V) = " + " ".join(
            [f"P({v} | {', '.join(self.pa[v])})" if self.pa[v] else f"P({v})" for v in self.v]
        )
        return factorization

    def path(self, X, Y):        
        def dfs(current, target, visited, path):
            if current == target:
                print(path)
                return

            visited.add(current)

            # Explore both types of edges in one go
            for neighbor, edge in (
                [(child, "->") for child in self.ch[current]] +  # directed edge ->
                [(parent, "<-") for parent in self.pa[current]] +  # directed edge <-
                [(n, "<->") for n in self.ne[current]]  # bidirected edge <->
            ):
                if neighbor not in visited:
                    dfs(neighbor, target, visited, path + f" {edge} {neighbor}")

            visited.remove(current)

        dfs(X, Y, set(), f"{X}")

    def ancestors(self, nodes):

        ancestors = set(nodes)
        changed = True
        while changed:
            new_ancestors = ancestors.copy()
            for node in ancestors:
                new_ancestors.update(self.pa[node])  # Add the parents of the current ancestors
            changed = (new_ancestors != ancestors)
            ancestors = new_ancestors
        return ancestors

    def d_separation_check(self, X, Y, Z, verbose=False):

        # Step 1: Let A = An(X, Y, Z)
        A = self.ancestors(X | Y | Z)

        if verbose:
            print(f"Ancestors of X, Y, Z: {A}")

        # Step 2 & 3: Initialize a subgraph G_A and add undirected edges for A \ Z
        subgraph = {v: set() for v in A}
        for u, v in self.de + self.be:
            if u in A - Z and v in A - Z:
                subgraph[u].add(v)
                subgraph[v].add(u)

        # Step 4: Add undirected edges for collider structures
        for Vk in A:
            parents = list(set(self.pa[Vk]) | set(self.ne[Vk]))
            if len(parents) >= 2 and Vk in self.ancestors(Z):
                for Vi in parents:
                    for Vj in parents:
                        if Vi != Vj:
                            subgraph[Vi].add(Vj)
                            subgraph[Vj].add(Vi)

        if verbose:
            print(f"Subgraph: {subgraph}")

        # Step 5: DFS to check reachability from X to Y
        visited = set()

        def dfs(node):
            if node in visited:
                return False
            if node in Y:
                return True
            visited.add(node)
            return any(dfs(neighbor) for neighbor in subgraph[node])

        return not any(dfs(node) for node in X)
