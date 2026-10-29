"""Small, independently checkable witnesses for necessary layout conditions.

These witnesses explain some infeasible requests. Absence of a witness does not
establish feasibility of the full rectangle-packing and routing problem.
"""
import hashlib
import json
import math
from .model import DiagramError


class LayoutConflict(DiagramError):
    def __init__(self,message,certificate,diagram):
        super().__init__(message)
        self.certificate = certificate
        self.fitted_diagram = diagram.to_dict()


def subject_hash(diagram,flow,gap,padding):
    subject = {"canvas":[diagram.width,diagram.height],"flow":flow,"gap":gap,"padding":padding,
               "nodes":sorted((n.id,n.width,n.height) for n in diagram.nodes),
               "edges":sorted((e.id,e.source,e.target) for e in diagram.edges)}
    return hashlib.sha256(json.dumps(subject,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def diagnose(diagram,flow="free",gap=24,padding=16):
    diagram.validate()
    if flow not in {"free","vertical","horizontal"} or not all(math.isfinite(v) and v>=0 for v in [gap,padding]):
        raise DiagramError("Invalid conflict-analysis options")
    base = {"schema_version":1,"subject_sha256":subject_hash(diagram,flow,gap,padding),
            "flow":flow,"gap":gap,"padding":padding,
            "scope":"Necessary-condition witness for fitted rectangular geometry; not an author-intent judgment or a minimum repair"}
    for n in diagram.nodes:
        for axis,extent,available in [("width",n.width,diagram.width-2*padding),("height",n.height,diagram.height-2*padding)]:
            if extent>available+1e-7:
                return {**base,"kind":"node_canvas","node_id":n.id,"axis":axis,
                        "required":extent,"available":available,"shortfall":extent-available}
    if flow!="free":
        nodes={n.id:n for n in diagram.nodes}
        outgoing={n.id:[] for n in diagram.nodes}
        for e in diagram.edges:
            outgoing[e.source].append(e)
        color,stack,active_edges,order = {},[],[],[]
        cycle=None
        def visit(u):
            nonlocal cycle
            color[u]=1
            stack.append(u)
            for e in outgoing[u]:
                v=e.target
                if color.get(v)==1:
                    start=stack.index(v)
                    cycle=(stack[start:]+[v],active_edges[start:]+[e.id])
                    return
                if not color.get(v):
                    active_edges.append(e.id)
                    visit(v)
                    active_edges.pop()
                    if cycle:
                        return
            stack.pop()
            color[u]=2
            order.append(u)
        for n in diagram.nodes:
            if not color.get(n.id):
                visit(n.id)
                if cycle:
                    break
        extent=lambda identifier: nodes[identifier].height if flow=="vertical" else nodes[identifier].width
        if cycle:
            identifiers,edges=cycle
            total=sum(extent(u)+gap for u in identifiers[:-1])
            return {**base,"kind":"positive_flow_cycle","node_ids":identifiers,"edge_ids":edges,
                    "cycle_increment":total,"contradiction":f"0 >= {total:g}"}
        longest={key:extent(key) for key in nodes}
        predecessor={}
        for u in reversed(order):
            for e in outgoing[u]:
                value=longest[u]+gap+extent(e.target)
                if value>longest[e.target]:
                    longest[e.target]=value
                    predecessor[e.target]=e
        if longest:
            end=max(longest,key=longest.get)
            required=longest[end]+2*padding
            available=diagram.height if flow=="vertical" else diagram.width
            if required>available+1e-7:
                identifiers,edges=[end],[]
                while identifiers[-1] in predecessor:
                    e=predecessor[identifiers[-1]]
                    edges.append(e.id); identifiers.append(e.source)
                return {**base,"kind":"flow_span","node_ids":list(reversed(identifiers)),
                        "edge_ids":list(reversed(edges)),"axis":"height" if flow=="vertical" else "width",
                        "required":required,"available":available,"shortfall":required-available}
    required=sum(n.width*n.height for n in diagram.nodes)
    available=max(0,diagram.width-2*padding)*max(0,diagram.height-2*padding)
    if required>available+1e-7:
        return {**base,"kind":"area_bound","node_ids":[n.id for n in diagram.nodes],
                "required":required,"available":available,"shortfall":required-available}
    return None


def verify_certificate(diagram,certificate,flow="free",gap=24,padding=16):
    """Check arithmetic and referenced inequalities without a solver or diagnose()."""
    try:
        diagram.validate()
        if flow not in {"free","vertical","horizontal"} or not all(math.isfinite(v) and v>=0 for v in [gap,padding]):
            return False
        c=certificate
        if c.get("schema_version")!=1 or c.get("subject_sha256")!=subject_hash(diagram,flow,gap,padding):
            return False
        if (c["flow"],c["gap"],c["padding"])!=(flow,gap,padding):
            return False
        nodes={n.id:n for n in diagram.nodes}
        edges={e.id:e for e in diagram.edges}
        def equal(a,b):
            return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7)
        kind=c["kind"]
        if kind=="node_canvas":
            n=nodes[c["node_id"]]
            if c["axis"] not in {"width","height"}:
                return False
            required=getattr(n,c["axis"])
            available=getattr(diagram,c["axis"])-2*padding
        elif kind=="area_bound":
            if len(c["node_ids"])!=len(nodes) or set(c["node_ids"])!=set(nodes):
                return False
            required=sum(n.width*n.height for n in diagram.nodes)
            available=max(0,diagram.width-2*padding)*max(0,diagram.height-2*padding)
        elif kind in {"positive_flow_cycle","flow_span"}:
            if flow not in {"vertical","horizontal"}:
                return False
            ids,edge_ids=c["node_ids"],c["edge_ids"]
            if len(ids)<2 or len(edge_ids)!=len(ids)-1 or len(set(edge_ids))!=len(edge_ids):
                return False
            if any(edges[key].source!=u or edges[key].target!=v for u,v,key in zip(ids,ids[1:],edge_ids)):
                return False
            extents=[nodes[u].height if flow=="vertical" else nodes[u].width for u in ids]
            if kind=="positive_flow_cycle":
                total=sum(v+gap for v in extents[:-1])
                return ids[0]==ids[-1] and len(set(ids[:-1]))==len(ids)-1 and total>0 and equal(c["cycle_increment"],total)
            if len(set(ids))!=len(ids) or c["axis"]!=("height" if flow=="vertical" else "width"):
                return False
            required=sum(extents)+gap*(len(ids)-1)+2*padding
            available=diagram.height if flow=="vertical" else diagram.width
        else:
            return False
        return required>available+1e-7 and equal(c["required"],required) and equal(c["available"],available) and equal(c["shortfall"],required-available)
    except (KeyError,ValueError,TypeError,AttributeError,IndexError):
        return False


def explain(certificate):
    c=certificate
    if c["kind"]=="positive_flow_cycle":
        return "No feasible flow layout: cycle "+" → ".join(c["node_ids"])+f" implies {c['contradiction']}"
    if c["kind"]=="flow_span":
        return f"No feasible flow layout: {' → '.join(c['node_ids'])} needs {c['required']:g} units of {c['axis']}, but the canvas has {c['available']:g}"
    if c["kind"]=="node_canvas":
        return f"Infeasible canvas: node {c['node_id']} needs {c['required']:g} units of {c['axis']}, but only {c['available']:g} remain after padding"
    return f"Infeasible canvas: fitted rectangles need area {c['required']:g}, but the padded canvas has area {c['available']:g}"
