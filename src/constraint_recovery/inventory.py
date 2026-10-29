"""Non-rendering source inventory. Candidates are observations, not graph labels."""
from collections import Counter
import hashlib
import math
import numpy as np
from defusedxml import ElementTree as SafeET
from .geometry import transform,point,numbers
from .model import DiagramError
from .svg import guard_xml,local,number

PRIMITIVES = {"rect","circle","ellipse","line","polyline","polygon","path","text","image","use"}


def bounds(points):
    x,y = zip(*points)
    return [min(x),min(y),max(x),max(y)]


def primitive_bounds(e,matrix):
    tag = local(e.tag)
    if tag in {"rect","image"}:
        x,y = number(e.get("x"),0),number(e.get("y"),0)
        w,h = number(e.get("width")),number(e.get("height"))
        if min(w,h)<0:
            raise DiagramError("Negative primitive size")
        return bounds([point(matrix,a,b) for a,b in [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]]),"exact affine axis-aligned envelope"
    if tag in {"circle","ellipse"}:
        cx,cy = number(e.get("cx"),0),number(e.get("cy"),0)
        rx = number(e.get("r")) if tag=="circle" else number(e.get("rx"))
        ry = rx if tag=="circle" else number(e.get("ry"))
        if min(rx,ry)<0:
            raise DiagramError("Negative primitive radius")
        x,y = point(matrix,cx,cy)
        dx,dy = np.sqrt((matrix[:2,0]*rx)**2+(matrix[:2,1]*ry)**2)
        return [x-dx,y-dy,x+dx,y+dy],"exact affine axis-aligned envelope"
    if tag=="line":
        return bounds([point(matrix,number(e.get(f"x{i}"),0),number(e.get(f"y{i}"),0)) for i in [1,2]]),"exact affine axis-aligned envelope"
    if tag in {"polygon","polyline"}:
        values = numbers(e.get("points",""))
        if len(values)<4 or len(values)%2:
            raise DiagramError("Invalid point list")
        return bounds([point(matrix,*values[i:i+2]) for i in range(0,len(values),2)]),"exact affine axis-aligned envelope"
    if tag=="path":
        try:
            from svgpathtools import parse_path
            path = parse_path(e.get("d",""))
            if not path:
                raise ValueError("empty path")
            x0,x1,y0,y1 = path.bbox()
        except Exception as exc:
            raise DiagramError(f"Path bounds unavailable: {type(exc).__name__}") from exc
        return bounds([point(matrix,x,y) for x,y in [(x0,y0),(x0,y1),(x1,y0),(x1,y1)]]),"conservative transformed local envelope"
    raise DiagramError("No independent bounds for text or referenced artwork")


def inspect_svg(text,max_primitives=10000):
    """Inspect XML without executing, rendering or fetching referenced resources.

    This accepts more syntax than the editor. It is never an SVG sanitizer and
    must not be used to authorize embedding the inspected original in a browser.
    """
    guard_xml(text)
    try:
        root = SafeET.fromstring(text)
    except Exception as exc:
        raise DiagramError(f"Invalid or unsafe XML: {exc}") from exc
    if local(root.tag)!="svg":
        raise DiagramError("Expected an SVG root")
    if max_primitives<1:
        raise DiagramError("Inventory primitive budget must be positive")
    vb = numbers(root.get("viewBox",""))
    if vb and (len(vb)!=4 or min(vb[2:])<=0):
        raise DiagramError("Invalid viewBox")
    canvas = vb if vb else [0,0,number(root.get("width")),number(root.get("height"))]
    if min(canvas[2:])<=0:
        raise DiagramError("Invalid inventory canvas")
    counts = Counter(local(e.tag) for e in root.iter())
    records = []
    references,active = Counter(),Counter()
    def visit(e,parent_matrix,path,in_defs=False,parent_failure=None):
        tag = local(e.tag)
        in_defs = in_defs or tag in {"defs","symbol","marker","pattern","clipPath","mask"}
        failure = parent_failure
        try:
            matrix = parent_matrix@transform(e.get("transform",""),allow_affine=True)
        except DiagramError as exc:
            matrix = parent_matrix
            failure = str(exc)
        for k,v in e.attrib.items():
            if local(k)=="href":
                references["fragment" if v.startswith("#") else "embedded" if v.startswith("data:") else "external"]+=1
            if local(k).lower().startswith("on"):
                active["event_attributes"]+=1
        if tag in {"script","foreignObject","animate","animateTransform","set"}:
            active[tag]+=1
        if tag in PRIMITIVES and not in_defs:
            if len(records)>=max_primitives:
                raise DiagramError("Inventory exceeds primitive budget; no partial coverage reported")
            record = {"location":path,"source_id":e.get("id"),"tag":tag,
                      "bounds":None,"bounds_scope":None,"geometry_failure":failure,
                      "explicit_marker_end":"marker-end" in e.attrib}
            if not failure:
                try:
                    record["bounds"],record["bounds_scope"] = primitive_bounds(e,matrix)
                except DiagramError as exc:
                    record["geometry_failure"] = str(exc)
                if tag=="text":
                    record["characters"] = len("".join(e.itertext()))
                    try:
                        record["anchor"] = point(matrix,number(e.get("x")),number(e.get("y")))
                    except DiagramError:
                        record["anchor"] = None
            records.append(record)
        for i,child in enumerate(e):
            visit(child,matrix,f"{path}/{local(child.tag)}[{i}]",in_defs,failure)
    initial = np.eye(3)
    initial[:2,2] = -np.asarray(canvas[:2])
    visit(root,initial,"svg")
    rects = [r for r in records if r["tag"]=="rect" and r["bounds"]]
    anchored = [r for r in records if r.get("anchor") is not None]
    def contains(box,p):
        return box[0]<=p[0]<=box[2] and box[1]<=p[1]<=box[3]
    background = []
    for rect in rects:
        a,b,c,d = rect["bounds"]
        if a<=0 and b<=0 and c>=canvas[2] and d>=canvas[3]:
            background.append(rect["location"])
    candidates = [r for r in rects if r["location"] not in background]
    owners = [sum(contains(r["bounds"],t["anchor"]) for r in candidates) for t in anchored]
    summary = {"visible_primitives":len(records),"visible_tags":dict(Counter(r["tag"] for r in records)),
               "bounded_primitives":sum(r["bounds"] is not None for r in records),
               "canvas_covering_rectangles":len(background),"other_rectangles":len(candidates),
               "rectangles_containing_text_anchors":sum(any(contains(r["bounds"],t["anchor"]) for t in anchored) for r in candidates),
               "text_anchors":len(anchored),"text_anchors_with_zero_rect_owners":owners.count(0),
               "text_anchors_with_multiple_rect_owners":sum(v>1 for v in owners),
               "explicit_marker_end_attributes":sum(r["explicit_marker_end"] for r in records)}
    return {"schema_version":1,"source_sha256":hashlib.sha256(text.encode()).hexdigest(),
            "canvas_viewbox":canvas,"all_element_counts":dict(counts),"reference_counts":dict(references),
            "active_content_signals":dict(active),"summary":summary,"primitives":records,
            "limitations":["Inventory only: not an editable graph, semantic annotation, sanitizer or browser rendering check",
                           "CSS layout, visibility and paint are not resolved; stroke/filter extents are excluded",
                           "Text anchors are not glyph bounds; text with list coordinates or only tspan positions may lack an anchor",
                           "Referenced use/symbol artwork is not expanded; compound nodes and decorative rectangles are not classified"]}
