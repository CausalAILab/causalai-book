from collections import deque
from graphviz import Source


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

        self.desc = {v: self._get_descendants(v) for v in self.v}

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

    def _get_descendants(self, v):
        descendants = set()

        def dfs(current):
            for child in self.ch[current]:
                if child not in descendants:
                    descendants.add(child)
                    dfs(child)

        dfs(v)
        return descendants

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

        paths = []

        def dfs(current, target, visited, path):
            if current == target:
                paths.append(path)
                return

            visited.add(current)

            # Explore both types of edges in one go
            for neighbor, edge in (
                [(child, "->") for child in self.ch[current]] +  # directed edge ->
                [(parent, "<-") for parent in self.pa[current]] +  # directed edge <-
                [(n, "<->") for n in self.ne[current]]  # bidirected edge <->
            ):
                if neighbor not in visited:
                    dfs(neighbor, target, visited, path + [edge, neighbor])

            visited.remove(current)

        dfs(X, Y, set(), [X])

        return paths
    
    def d_separation_paths(self, X, Y, Z):

        blocked_paths = []
        unblocked_paths = []

        def is_blocked(path, Z):
            for i in range(2, len(path)-2, 2):
                collider = (path[i-1] in ["->", "<->"]) and (path[i+1] in ["<->", "<-"])
                if not collider and path[i] in Z:
                    return True
                elif collider and (path[i] not in Z) and (Z.intersection(self.desc[path[i]]) == set()):
                    return True
            return False

        for x in X:
            for y in Y:
                paths = self.path(x, y)
                for path in paths:
                    if is_blocked(path, Z):
                        blocked_paths.append(path)
                    else:
                        unblocked_paths.append(path)
        
        return blocked_paths, unblocked_paths

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
        # Algorithm 1 in the book

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

        
        def dfs(node, path):
            if node in visited:
                return None
            if node in Y:
                return path + [node]  # Return the path when Y is found
            visited.add(node)
            for neighbor in subgraph[node]:
                result = dfs(neighbor, path + [node])
                if result:
                    return result
            return None

        for node in X:
            path = dfs(node, [])
            if path:
                return False, path, subgraph  # Return the path if found

        return True, None, subgraph


def parse_path_to_edges(path):

    edges = set()

    i = 0
    while i < len(path) - 2:
        u = path[i]
        edge = path[i+1]
        v = path[i+2]

        if edge == '->':  # Directed edge u -> v
            edges.add((u, v, 'directed'))
        elif edge == '<-':  # Directed edge v -> u (reverse direction)
            edges.add((v, u, 'directed'))
        elif edge == '<->':  # Bidirected edge u <-> v
            edges.add((u, v, 'bidirected'))
        
        i += 2

    return edges

def directed_graph_to_dot(graph, name="Causal Diagram", Z=set(), paths=[]):
        
        dot_text = f"digraph {name}" + " {\n"

        dot_text += " rankdir=LR;\n"

        # Nodes
        dot_text += " node [shape=circle, fontsize=16, style=filled];\n"
        for node in graph.v:
            color = "#add8e6" if node in Z else "white"
            dot_text += f' {node} [fillcolor="{color}"];\n'

        edges = set()
        for path in paths:
            edges |= parse_path_to_edges(path)

        # Adding directed edges to DOT (unblocked paths in red)
        for u, v in graph.de:
            color = "red" if (u, v, 'directed') in edges else "black"
            dot_text += f' {u} -> {v} [color="{color}"];\n'

        # Adding bidirected edges to DOT (unblocked paths in red)
        for u, v in graph.be:
            color = "red" if (u, v, 'bidirected') in edges else "black"
            dot_text += f' {u} -> {v} [dir=both, style=dashed, color="{color}"];\n'

        dot_text += "}\n"
        return dot_text

def plot_causal_diagram(graph, name="Causal Diagram", Z=set(), paths=[]):
    dot_text = directed_graph_to_dot(graph, name, Z, paths)
    return Source(dot_text)

def undirected_graph_to_dot(graph, name="Causal Diagram", path=[]):

    dot_text = f"graph {name}" + " {\n"

    dot_text += " rankdir=LR;\n"

    dot_text += " node [shape=circle, fontsize=16, style=filled, fillcolor=white];\n"

    path = [(path[i], path[i+1]) for i in range(0, len(path)-1)]
    
    # Iterate over the graph dictionary and add edges to the DOT representation
    added_edges = set()  # To ensure edges are not duplicated
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            if (neighbor, node) not in added_edges:
                color = "red" if (node, neighbor) in path or (neighbor, node) in path else "black"
                dot_text += f' {node} -- {neighbor} [color="{color}"];\n'
                added_edges.add((node, neighbor))
                added_edges.add((neighbor, node))
    
    # Close the DOT text
    dot_text += "}\n"
    
    return dot_text

def plot_undirected_graph(graph, name="Causal Diagram", path=[]):
    dot_text = undirected_graph_to_dot(graph, name, path)
    return Source(dot_text)