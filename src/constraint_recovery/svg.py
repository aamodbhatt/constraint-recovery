"""Strict, deliberately narrow SVG import and normalized export.

No transforms, CSS, scripts, external resources, curves, or raster content.
Unsupported content fails explicitly rather than silently disappearing.
"""
import math
import re
import xml.etree.ElementTree as ET
from defusedxml import ElementTree as SafeET
from .model import Diagram, DiagramError, Edge, Node

NS = "http://www.w3.org/2000/svg"
NUM = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"


def local(tag):
    return tag.rsplit("}", 1)[-1]


def number(value, default=None):
    if value is None:
        if default is None:
            raise DiagramError("Missing required numeric SVG attribute")
        return float(default)
    if not re.fullmatch(NUM + r"(?:px)?", value.strip()):
        raise DiagramError(f"Unsupported numeric SVG value: {value}")
    result = float(value.removesuffix("px"))
    if not math.isfinite(result):
        raise DiagramError("SVG numbers must be finite")
    return result


def boundary_distance(p, n):
    x, y = p
    dx = max(n.x-x, 0, x-n.x-n.width)
    dy = max(n.y-y, 0, y-n.y-n.height)
    if dx or dy:
        return math.hypot(dx, dy)
    return min(x-n.x, n.x+n.width-x, y-n.y, n.y+n.height-y)


def endpoint(p, nodes, tolerance):
    ranked = sorted((boundary_distance(p, n), n.id) for n in nodes)
    if not ranked or ranked[0][0] > tolerance:
        raise DiagramError(f"Unattached arrow endpoint {p}; maximum distance {tolerance}px")
    plausible = [i for distance, i in ranked if distance <= tolerance and distance <= ranked[0][0]+2]
    if len(plausible) != 1:
        raise DiagramError(f"Ambiguous arrow endpoint {p}: {plausible}; review the drawing")
    return plausible[0]


def guard_xml(text):
    # ElementTree discards processing instructions; check before preserving or
    # embedding the original source, where a browser could still interpret them.
    if re.search(r"<\?(?!xml(?:\s|\?>))",text,re.I) or "<!DOCTYPE" in text.upper():
        raise DiagramError("SVG processing instructions and document types are unsupported")


def parse_svg(text, tolerance=8, attachment_model=None):
    guard_xml(text)
    try:
        root = SafeET.fromstring(text)
    except Exception as exc:
        raise DiagramError(f"Invalid or unsafe XML: {exc}") from exc
    if local(root.tag) != "svg":
        raise DiagramError("Expected an SVG root")
    allowed = {"svg", "g", "rect", "text", "tspan", "line", "polyline", "path", "defs", "marker", "title", "desc"}
    defs_ids = set()
    for defs in root.iter():
        if local(defs.tag) == "defs":
            defs_ids.update(id(e) for e in defs.iter())
    for e in root.iter():
        if local(e.tag) not in allowed:
            raise DiagramError(f"Unsupported element: {local(e.tag)}")
        for k, v in e.attrib.items():
            if local(k).lower().startswith("on") or local(k) in {"href", "style", "transform", "class"}:
                raise DiagramError(f"Unsupported attribute {k}; flatten SVG styles/transforms first")
            if "url(" in v and not re.fullmatch(r"url\(#[A-Za-z_][\w.-]*\)", v):
                raise DiagramError("External SVG resources are unsupported")
        if local(e.tag) == "g" and any(k in e.attrib for k in ["fill", "stroke", "font-size", "font-family"]):
            raise DiagramError("Inherited group styles are unsupported; place styles on primitives")
    vb = [float(v) for v in re.findall(NUM, root.get("viewBox", ""))]
    if vb and (len(vb) != 4 or vb[:2] != [0, 0]):
        raise DiagramError("Only a zero-origin viewBox is supported")
    width = number(root.get("width"), vb[2] if vb else None)
    height = number(root.get("height"), vb[3] if vb else None)
    if vb and (abs(vb[2]-width) > 1e-6 or abs(vb[3]-height) > 1e-6):
        raise DiagramError("Canvas and viewBox dimensions must agree; normalize units first")
    nodes, texts, connectors = [], [], []
    for e in root.iter():
        tag = local(e.tag)
        if id(e) in defs_ids:
            continue
        if tag == "rect":
            nodes.append(Node(e.get("id", f"node-{len(nodes)}"), number(e.get("x"), 0),
                              number(e.get("y"), 0), number(e.get("width")), number(e.get("height")),
                              fill=e.get("fill", "#eef3fb"), stroke=e.get("stroke", "#30445f")))
        elif tag == "text":
            texts.append(e)
        elif tag in {"line", "polyline", "path"}:
            if "marker-end" not in e.attrib:
                raise DiagramError("Only directed connectors with marker-end are supported")
            if tag == "line":
                pts = [[number(e.get("x1")), number(e.get("y1"))], [number(e.get("x2")), number(e.get("y2"))]]
            elif tag == "polyline":
                raw = e.get("points", "")
                vals = [float(v) for v in re.findall(NUM, raw)]
                if re.sub(NUM, "", raw).strip(" ,\n\t") or len(vals) < 4 or len(vals) % 2:
                    raise DiagramError("Invalid polyline points")
                pts = [vals[i:i+2] for i in range(0, len(vals), 2)]
            else:
                raw = e.get("d", "")
                tokens = re.findall(NUM + r"|[A-Za-z]", raw)
                if re.sub(NUM + r"|[ML]", "", raw).strip(" ,\n\t"):
                    raise DiagramError("Only absolute M/L connector paths are supported")
                pts, i = [], 0
                while i < len(tokens):
                    if tokens[i] not in {"M", "L"} or i+2 >= len(tokens):
                        raise DiagramError("Use explicit M/L coordinate pairs")
                    pts.append([float(tokens[i+1]), float(tokens[i+2])])
                    i += 3
                if len(pts) < 2:
                    raise DiagramError("Connector must have at least two points")
            connectors.append((e.get("id", f"edge-{len(connectors)}"), pts))
    if not nodes:
        raise DiagramError("No supported rectangular nodes found")
    # Reject invalid node geometry before any learned feature extraction.
    Diagram(width,height,nodes,[]).validate()
    for e in texts:
        x, y = number(e.get("x")), number(e.get("y"))
        candidates = [n for n in nodes if n.x <= x <= n.x+n.width and n.y <= y <= n.y+n.height]
        if len(candidates) != 1:
            raise DiagramError(f"Text at {(x,y)} has {len(candidates)} possible owning nodes")
        n = candidates[0]
        if n.label:
            raise DiagramError(f"Multiple text elements in {n.id}; combine using tspans")
        spans = [c for c in e if local(c.tag) == "tspan"]
        n.lines = ["".join(c.itertext()) for c in spans] if spans else ["".join(e.itertext())]
        n.label = " ".join(n.lines)
        n.font_size = number(e.get("font-size"), 16)
    edges = []
    for i,p in connectors:
        if attachment_model is None:
            source,target = endpoint(p[0],nodes,tolerance),endpoint(p[-1],nodes,tolerance)
        else:
            source = attachment_model.resolve(p[0],[p[0][k]-p[1][k] for k in range(2)],nodes)
            target = attachment_model.resolve(p[-1],[p[-1][k]-p[-2][k] for k in range(2)],nodes)
        edge = Edge(i,source,target,p)
        if attachment_model is not None:
            edge.evidence = "Experimental synthetic-trained endpoint ranker; review required; scores are not correctness guarantees"
        edges.append(edge)
    return Diagram(width, height, nodes, edges,
                   [("Experimental learned geometric attachment recovery. Review required." if attachment_model else
                     "Geometric baseline only. Review recovered arrow attachments before treating them as semantic constraints."),
                    "Export normalizes typography, node styling, and connectors; this is not a lossless SVG editor."]+
                   (["Experimental learned attachment selection enabled; synthetic validation only"] if attachment_model else [])).validate()


def route(a, b):
    ac = (a.x+a.width/2, a.y+a.height/2)
    bc = (b.x+b.width/2, b.y+b.height/2)
    if abs(bc[0]-ac[0]) >= abs(bc[1]-ac[1]):
        forward = bc[0] >= ac[0]
        start = [a.x+a.width if forward else a.x, ac[1]]
        end = [b.x if forward else b.x+b.width, bc[1]]
    else:
        forward = bc[1] >= ac[1]
        start = [ac[0], a.y+a.height if forward else a.y]
        end = [bc[0], b.y if forward else b.y+b.height]
    return [start, end]


def render_svg(d):
    ET.register_namespace("", NS)
    def el(parent, tag, **attrs):
        return ET.SubElement(parent, f"{{{NS}}}{tag}", {k.replace("_", "-"): str(v) for k,v in attrs.items()})
    root = ET.Element(f"{{{NS}}}svg", {"width": str(d.width), "height": str(d.height), "viewBox": f"0 0 {d.width} {d.height}"})
    marker_id = "cr-arrow"
    existing = {n.id for n in d.nodes} | {e.id for e in d.edges}
    while marker_id in existing:
        marker_id += "-marker"
    defs = el(root, "defs")
    marker = el(defs, "marker", id=marker_id, markerWidth=8, markerHeight=8, refX=8, refY=4, orient="auto", markerUnits="userSpaceOnUse")
    el(marker, "path", d="M0,0 L8,4 L0,8 Z", fill="#30445f")
    for e in d.edges:
        el(root, "polyline", id=e.id, points=" ".join(f"{x},{y}" for x,y in e.points), fill="none", stroke="#30445f", stroke_width=1.8, marker_end=f"url(#{marker_id})")
    for n in d.nodes:
        el(root, "rect", id=n.id, x=n.x, y=n.y, width=n.width, height=n.height, rx=8, fill=n.fill, stroke=n.stroke, stroke_width=1.5)
        lines = n.lines or [n.label]
        y = n.y+n.height/2-(len(lines)-1)*n.font_size*.65+n.font_size*.33
        text = el(root, "text", x=n.x+n.width/2, y=y, font_size=n.font_size, font_family="Arial, sans-serif", text_anchor="middle", fill="#172c47")
        for j, line in enumerate(lines):
            el(text, "tspan", x=n.x+n.width/2, y=y+j*n.font_size*1.3).text = line
    return ET.tostring(root, encoding="unicode")
