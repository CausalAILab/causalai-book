from graphviz import Source

def convert_to_dot(graph, path_1 = [], path_2 = [], nodes = [], node_positions = {}):
    
    dot_str = "digraph G {\n  rankdir=LR;\n"

    def get_edges_from_paths(paths):
        edges = []
        for path in paths:
            for edge in path.edges:
                edges.append(edge.edge)
        return edges
    
    path_1_edges = get_edges_from_paths(path_1)
    path_2_edges = get_edges_from_paths(path_2)

    # Add nodes with positions
    for node in graph.nodes:
        pos = f'pos="{node_positions[node["name"]][0]},{node_positions[node["name"]][1]}!"' if node['name'] in node_positions else ""
        fillcolor = 'style=filled, fillcolor=lightblue' if node['name'] in nodes else ""
        dot_str += f'  {node["name"]} [label="{node["label"]}" {pos} {fillcolor}];\n'
  
    # Add edges
    for edge in graph.edges:
        color = "red" if edge in path_1_edges else \
                "lightgreen" if edge in path_2_edges else ""
        style = f'color={color}, penwidth=2.0' if color else ""
        arrow_type = f'[dir=both, style=dashed, constraint=false, splines=curved, {style}]' if edge['type_'] == 'bidirected' else f'[{style}]'
        dot_str += f'  {edge["from_"]} -> {edge["to_"]} {arrow_type};\n'

    return dot_str + "}"


def plot_causal_diagram(graph, path_1 = [], path_2 = [], nodes = [], node_positions = {}):
    dot_text = convert_to_dot(graph, path_1, path_2, nodes, node_positions)
    return Source(dot_text, engine='neato')