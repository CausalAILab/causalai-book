from graphviz import Source

from src.inference.utils.expression_utils import ExpressionUtils as eu


def convert_to_dot(graph, path_1=[], path_2=[], nodes=[], node_positions={}):

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
        pos = (
            f'pos="{node_positions[node["name"]][0]},{node_positions[node["name"]][1]}!"'
            if node["name"] in node_positions
            else ""
        )
        fillcolor = "style=filled, fillcolor=lightblue" if node["name"] in nodes else ""
        dot_str += f'  {node["name"]} [label="{node["label"]}" {pos} {fillcolor}];\n'

    # Add edges
    for edge in graph.edges:
        color = (
            "red"
            if edge in path_1_edges
            else "lightgreen" if edge in path_2_edges else ""
        )
        style = f"color={color}, penwidth=2.0" if color else ""
        arrow_type = (
            f"[dir=both, style=dashed, constraint=false, splines=curved, {style}]"
            if edge["type_"] == "bidirected"
            else f"[{style}]"
        )
        dot_str += f'  {edge["from_"]} -> {edge["to_"]} {arrow_type};\n'

    return dot_str + "}"


def plot_causal_diagram(graph, path_1=[], path_2=[], nodes=[], node_positions={}):
    dot_text = convert_to_dot(graph, path_1, path_2, nodes, node_positions)
    return Source(dot_text, engine="neato")


def display_inspector_result(result, latex=False):

    if result is None:
        return None

    if latex:
        from IPython.display import Latex, display

        display(Latex("$\\text{Applicable: }" + f"{result.applicable}$"))
        display(
            Latex("$\\text{Expression: }" + f"{eu.write(result.expression, True)}$")
        )
        display(
            Latex("$\\text{Evaluation: }" + f"{eu.write(result.independence, True)}$")
        )

        if result.applicable:
            display(
                Latex(
                    "$\\text{Result: }"
                    + f'{eu.write(eu.create("=", [result.expression, result.inference]), True)}$'
                )
            )
        else:
            display(
                Latex(
                    "$\\text{Result: }"
                    + f'{eu.write(eu.create("!=", [result.expression, result.inference]), True)}$'
                )
            )

    else:

        print("Applicable:", result.applicable)
        print("Expression:", eu.write(result.expression))
        print("Evaluation:", eu.write(result.independence))

        if result.applicable:
            print(
                "Result:",
                eu.write(eu.create("=", [result.expression, result.inference])),
            )
        else:
            print(
                "Result:",
                eu.write(eu.create("!=", [result.expression, result.inference])),
            )


def do_calculus_derivation(trace):

    from IPython.display import HTML, Latex, Math, display

    op_dict = {
        0: "base",
        1: "rule 3",
        2: "summation over variable",
        3: "factorize",
        4: "rule 2",
        5: "conditional probability",
        6: "c-component form",
        7: "subgoal",
        8: "compute numerator",
        9: "compute denominator",
        10: "compute factor",
        11: "transport",
        12: "same domain experiment",
        13: "c-component",
        20: "factor fraction",
        21: "factor terminal",
        22: "factor subgoal",
        23: "sum ancenstors",
        24: "c-decomposition",
        25: "transportation",
    }

    strings = []

    def print_step(trace, level=1):

        if trace.query is None:
            return

        if level == 0:
            strings.append(
                f"{eu.write(trace.query)} ...................... \\text{{({op_dict[trace.algorithmInfo['line']]})}}"
            )
        else:
            strings.append(
                f"= {eu.write(trace.query)} ...................... \\text{{({op_dict[trace.algorithmInfo['line']]})}}"
            )

        if trace.children is not None:
            if len(trace.children) > 1:
                for child in trace.children:
                    print_step(child, 0)
            else:
                print_step(trace.children[0])

        return

    print_step(trace, 0)

    for string in strings:
        display(Latex(string))
