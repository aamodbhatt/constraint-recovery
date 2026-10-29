"""Read-only checks, separate from layout optimization."""
from .svg import boundary_distance
from .typography import text_width


def segment_hits_rect(p, q, n, eps=1e-5):
    # Clip the segment against the open interior of the rectangle.
    lo, hi = 0., 1.
    for a, b, low, high in [(p[0], q[0], n.x+eps, n.x+n.width-eps),
                             (p[1], q[1], n.y+eps, n.y+n.height-eps)]:
        delta = b-a
        if abs(delta) < eps:
            if not low < a < high:
                return False
        else:
            u, v = sorted(((low-a)/delta, (high-a)/delta))
            lo, hi = max(lo, u), min(hi, v)
            if lo >= hi:
                return False
    return lo < hi


def verify(original, actual, expected_labels=None, minimum_font=0, flow="free", gap=0,expected_canvas=None):
    errors = []
    if expected_canvas is not None and (abs(actual.width-expected_canvas[0])>1e-4 or abs(actual.height-expected_canvas[1])>1e-4):
        errors.append("Serialized canvas does not match the requested dimensions")
    nodes = {n.id:n for n in actual.nodes}
    if set(nodes) != {n.id for n in original.nodes}:
        errors.append("Node identity set changed")
    expected = {n.id:n.label for n in original.nodes}
    expected.update(expected_labels or {})
    for n in actual.nodes:
        if n.id not in expected or n.label.split() != expected[n.id].split():
            errors.append(f"Protected or requested label changed: {n.id}")
        if n.x < -1e-4 or n.y < -1e-4 or n.x+n.width > actual.width+1e-4 or n.y+n.height > actual.height+1e-4:
            errors.append(f"Outside canvas: {n.id}")
        if n.font_size < minimum_font-1e-4:
            errors.append(f"Font too small: {n.id}")
        if max(text_width(line, n.font_size) for line in (n.lines or [n.label])) > n.width-20+1e-4:
            errors.append(f"Text exceeds node width: {n.id}")
        if len(n.lines or [n.label])*n.font_size*1.3 > n.height-16+1e-4:
            errors.append(f"Text exceeds node height: {n.id}")
    for i,a in enumerate(actual.nodes):
        for b in actual.nodes[i+1:]:
            if min(a.x+a.width,b.x+b.width)-max(a.x,b.x)>1e-4 and min(a.y+a.height,b.y+b.height)-max(a.y,b.y)>1e-4:
                errors.append(f"Nodes overlap: {a.id}, {b.id}")
    if {(e.id,e.source,e.target) for e in actual.edges} != {(e.id,e.source,e.target) for e in original.edges}:
        errors.append("Directed connector graph changed")
    for e in actual.edges:
        if e.source in nodes and e.target in nodes and flow!="free":
            a,b = nodes[e.source],nodes[e.target]
            end,start = (a.y+a.height,b.y) if flow=="vertical" else (a.x+a.width,b.x)
            if start-end < gap-1e-4:
                errors.append(f"Requested flow order or gap violated: {e.id}")
        if any(x<0 or y<0 or x>actual.width or y>actual.height for x,y in e.points):
            errors.append(f"Connector outside canvas: {e.id}")
        if len(e.points)<2:
            errors.append(f"Missing connector path: {e.id}")
            continue
        for point,key in [(e.points[0],e.source),(e.points[-1],e.target)]:
            if key not in nodes or boundary_distance(point,nodes[key])>1e-3:
                errors.append(f"Detached connector: {e.id}")
        if any(segment_hits_rect(p,q,n) for p,q in zip(e.points,e.points[1:]) for n in actual.nodes):
            errors.append(f"Connector crosses a node interior: {e.id}")
    return {"passed":not errors,"errors":errors,
            "scope":"Checks accepted graph, geometry and conservative font metrics; does not prove inferred author intent or pixel-perfect browser typography."}
