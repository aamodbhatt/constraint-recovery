"""Explicit requested graph changes, separate from inferred source relationships."""
from copy import deepcopy
from .model import DiagramError,Edge,Node


def add_branch(diagram,source,new_id,label):
    diagram.validate()
    result = deepcopy(diagram)
    known = {n.id:n for n in result.nodes}
    all_ids = set(known)|{e.id for e in result.edges}
    if source not in known:
        raise DiagramError(f"Unknown branch source: {source}")
    if not new_id or not label.strip() or new_id in all_ids:
        raise DiagramError("Branch needs a nonempty label and an unused node ID")
    if any(c.isspace() for c in new_id):
        raise DiagramError("Branch node IDs cannot contain whitespace")
    parent = known[source]
    result.nodes.append(Node(new_id,parent.x,parent.y+parent.height+24,parent.width,parent.height,
                             label,parent.font_size,parent.fill,parent.stroke))
    edge_id = f"branch-{source}-{new_id}"
    while edge_id in all_ids or edge_id==new_id:
        edge_id += "-edge"
    result.edges.append(Edge(edge_id,source,new_id,evidence="Explicit user-requested branch insertion"))
    return result.validate()
