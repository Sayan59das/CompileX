"""Test cases and samples as the plain stdin / stdout text the game sends to a program.

The templates keep their inputs as Python values (a list, a list of edges, a dict of nodes, edges and a source). The service turns each
into text with these two functions before it types the question and serves it. They live here, with no dependencies, so that the
service and the tests that check what a served question looks like (the backend's diagram audit) use the very same code.
"""


def to_stdin(val) -> str:
    """Convert any value to plain-text stdin string."""
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (list, tuple)):
        # flat list/tuple of scalars → space-separated
        if all(isinstance(x, (int, float, str, bool)) for x in val):
            return " ".join(str(x) for x in val)
        # list of pairs (edges) → one "u v" per line
        if all(isinstance(x, (list, tuple)) and len(x) >= 2 for x in val):
            return "\n".join(" ".join(str(e) for e in pair) for pair in val)
        # nested list → one row per line
        return "\n".join(to_stdin(row) for row in val)
    if isinstance(val, dict):
        # Special handling for graph inputs: {"nodes": n, "edges": [...], "src": s, "dst": d}
        # and weighted graphs: {"nodes": n, "edges": [(u,v,w),...], "src": s}
        if "edges" in val and "nodes" in val:
            edges = val["edges"]
            n_nodes = val["nodes"]
            n_edges = len(edges)
            # Format edges as "u v" or "u v w" per line
            edge_lines = "\n".join(" ".join(str(e) for e in edge) for edge in edges)
            # Check for src/dst (BFS) or just src (Dijkstra)
            if "src" in val and "dst" in val:
                return f"{n_nodes} {n_edges}\n{edge_lines}\n{val['src']} {val['dst']}"
            elif "src" in val:
                header = f"{n_nodes} {n_edges} {val['src']}"
                return f"{header}\n{edge_lines}" if edge_lines else header
            else:
                return f"{n_nodes} {n_edges}\n{edge_lines}" if edge_lines else f"{n_nodes} {n_edges}"
        # Generic dict → one value per line
        lines = []
        for v in val.values():
            lines.append(to_stdin(v))
        return "\n".join(lines)
    return str(val)


def to_stdout(val) -> str:
    """Convert output value to expected stdout string."""
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        if all(isinstance(x, (int, float, str, bool)) for x in val):
            return " ".join(str(x) for x in val)
        return "\n".join(to_stdout(row) for row in val)
    return str(val)
