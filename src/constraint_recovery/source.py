"""Opt-in, source-bound editing for a conservative static SVG subset.

Geometry is recovered in viewBox units. The original element hierarchy and paint
definitions survive export; unsupported visible artwork is never silently dropped.
This is deliberately not a general browser SVG implementation.
"""
from copy import deepcopy
from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET
import numpy as np
from defusedxml import ElementTree as SafeET
from .geometry import numbers, transform, point, scale, curve_points
from .model import Diagram, DiagramError, Edge, Node
from .svg import NS, local, number, endpoint, guard_xml

PAINT = {"fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity",
         "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin",
         "stroke-miterlimit", "color", "opacity", "stop-color", "stop-opacity"}
TEXT = {"font-family", "font-size", "font-weight", "font-style", "text-anchor",
        "dominant-baseline", "alignment-baseline", "letter-spacing", "word-spacing"}
PROPERTIES = PAINT | TEXT | {"marker-start", "marker-mid", "marker-end", "display", "visibility"}
INHERITED = (PAINT - {"opacity", "stop-color", "stop-opacity"}) | TEXT | {"visibility", "marker-start", "marker-mid", "marker-end"}
DEFAULTS = {"fill":"black", "stroke":"none", "font-size":"16", "font-family":"serif",
            "font-weight":"normal", "font-style":"normal", "text-anchor":"start",
            "display":"inline", "visibility":"visible", "opacity":"1"}
DEFINITION_TAGS = {"defs", "marker", "linearGradient", "radialGradient", "stop"}
VISIBLE_TAGS = {"svg", "g", "rect", "text", "tspan", "line", "polyline", "path", "style", "title", "desc", "metadata"}


def dependencies():
    try:
        import cssselect2
        import tinycss2
        import svgpathtools  # noqa: F401; validate the complete optional extra
    except ImportError as exc:
        raise DiagramError("Extended SVG support needs the 'svg' extra: pip install 'constraint-recovery[svg]'") from exc
    return cssselect2, tinycss2


def safe_tokens(tokens):
    """Inspect decoded CSS tokens, including escaped URL spellings."""
    for token in tokens:
        if token.type == "error":
            raise DiagramError("Malformed CSS")
        if token.type == "url":
            if not re.fullmatch(r"#[A-Za-z_][\w.:-]*", token.value):
                raise DiagramError("Only local fragment CSS URLs are supported")
        if token.type == "function":
            if token.lower_name == "url":
                content = [v for v in token.arguments if v.type != "whitespace"]
                if len(content)!=1 or content[0].type!="string" or not re.fullmatch(r"#[A-Za-z_][\w.:-]*",content[0].value):
                    raise DiagramError("Only local fragment CSS URLs are supported")
            else:
                if token.lower_name not in {"rgb", "rgba", "hsl", "hsla"}:
                    raise DiagramError(f"Unsupported CSS function: {token.name}")
                safe_tokens(token.arguments)


def declarations(raw):
    _,css = dependencies()
    result = []
    for item in css.parse_declaration_list(raw,skip_whitespace=True,skip_comments=True):
        if item.type!="declaration" or item.lower_name not in PROPERTIES:
            raise DiagramError(f"Unsupported CSS declaration: {getattr(item,'lower_name',item.type)}")
        safe_tokens(item.value)
        value = css.serialize(item.value).strip()
        if value.lower() in {"initial", "unset", "revert", "revert-layer"}:
            raise DiagramError("CSS reset keywords are unsupported")
        result.append((item.lower_name,value,item.important))
    return result


def fragment_reference(value):
    _,css = dependencies()
    tokens = [t for t in css.parse_component_value_list(value) if t.type!="whitespace"]
    safe_tokens(tokens)
    if len(tokens)!=1:
        raise DiagramError("Expected one local SVG paint reference")
    token = tokens[0]
    if token.type=="url":
        return token.value[1:]
    if token.type=="function" and token.lower_name=="url":
        return [v for v in token.arguments if v.type!="whitespace"][0].value[1:]
    raise DiagramError("Expected a local URL reference")


def styles(root):
    cssselect2,css = dependencies()
    matcher = cssselect2.Matcher()
    for e in root.iter():
        if local(e.tag)!="style":
            continue
        if e.get("type","text/css")!="text/css" or e.get("media","all")!="all":
            raise DiagramError("Only unconditional text/css stylesheets are supported")
        for rule in css.parse_stylesheet(e.text or "",skip_comments=True,skip_whitespace=True):
            if rule.type!="qualified-rule":
                raise DiagramError("CSS at-rules and malformed stylesheets are unsupported")
            selector = css.serialize(rule.prelude)
            # State-dependent selectors cannot be resolved once for all renderings.
            if re.search(r":(?:hover|active|focus|visited|link|target|enabled|disabled|checked|not|is|where|has)\b",selector,re.I) or "::" in selector:
                raise DiagramError("Dynamic/functional CSS selectors are unsupported")
            try:
                compiled = cssselect2.compile_selector_list(selector)
            except cssselect2.SelectorError as exc:
                raise DiagramError(f"Unsupported CSS selector: {selector}") from exc
            payload = declarations(rule.content)
            for entry in compiled:
                matcher.add_selector(entry,payload)
    computed = {}
    for wrapper in cssselect2.ElementWrapper.from_xml_root(root).iter_subtree():
        e = wrapper.etree_element
        parent = computed.get(wrapper.parent.etree_element,{}) if wrapper.parent else {}
        values = dict(DEFAULTS)
        values.update({k:v for k,v in parent.items() if k in INHERITED})
        ranked = {}
        def offer(k,v,important,specificity,order):
            priority = (bool(important),specificity,order)
            if k not in ranked or priority>=ranked[k][0]:
                ranked[k] = (priority,v)
        for k,v in e.attrib.items():
            if k in PROPERTIES:
                safe_tokens(css.parse_component_value_list(v))
                offer(k,v,False,(0,0,0,0),-1)
        for specificity,order,pseudo,payload in matcher.match(wrapper):
            for k,v,important in payload:
                offer(k,v,important,(0,)+specificity,order)
        for k,v,important in declarations(e.get("style","")):
            offer(k,v,important,(1,0,0,0),0)
        for k,(_,value) in ranked.items():
            values[k] = parent.get(k,DEFAULTS.get(k,"")) if value=="inherit" else value
        computed[e] = values
    return computed


def validate_tree(root):
    if root.tag not in {"svg",f"{{{NS}}}svg"}:
        raise DiagramError("Expected an SVG root")
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    if len(ids)!=len(set(ids)):
        raise DiagramError("Duplicate source SVG IDs")
    def visit(e,in_defs=False):
        tag = local(e.tag)
        if e.tag.startswith("{") and not e.tag.startswith("{"+NS+"}"):
            raise DiagramError("Foreign XML namespaces are unsupported")
        if tag not in VISIBLE_TAGS | DEFINITION_TAGS:
            raise DiagramError(f"Unsupported element: {tag}")
        if tag in DEFINITION_TAGS and tag!="defs" and not in_defs:
            raise DiagramError(f"Definition outside defs: {tag}")
        if tag=="svg" and e is not root:
            raise DiagramError("Nested SVG viewports are unsupported")
        for k,v in e.attrib.items():
            key = local(k)
            if key.lower().startswith("on") or key in {"filter", "clip-path", "mask", "vector-effect", "textLength", "lengthAdjust", "rotate", "transform-origin", "transform-box", "writing-mode", "direction", "unicode-bidi", "requiredFeatures", "requiredExtensions", "systemLanguage"}:
                raise DiagramError(f"Unsupported attribute: {key}")
            if key=="href" and (not in_defs or not re.fullmatch(r"#[A-Za-z_][\w.:-]*",v)):
                raise DiagramError("Only local definition references are supported")
            if key=="base":
                raise DiagramError("XML base URLs are unsupported")
            if "url" in v.lower() and key!="style":
                _,css = dependencies()
                safe_tokens(css.parse_component_value_list(v))
        for child in e:
            visit(child,in_defs or tag=="defs")
    visit(root)


@dataclass
class Binding:
    index: int
    matrix: np.ndarray
    style: dict


class SourceDocument:
    def __init__(self,text,tolerance=8,attachment_model=None,attachment_overrides=None,review=False):
        dependencies()
        guard_xml(text)
        try:
            self.root = SafeET.fromstring(text)
        except Exception as exc:
            raise DiagramError(f"Invalid or unsafe XML: {exc}") from exc
        validate_tree(self.root)
        self.text = text
        self.computed = styles(self.root)
        vb = numbers(self.root.get("viewBox",""))
        if vb and (len(vb)!=4 or min(vb[2:])<=0):
            raise DiagramError("Invalid viewBox")
        if vb:
            self.origin = vb[:2]
            width,height = vb[2:]
        else:
            self.origin = [0,0]
            width,height = number(self.root.get("width")),number(self.root.get("height"))
        self.nodes,self.edges,self.texts = {},{},{}
        elements = list(self.root.iter())
        indices = {e:i for i,e in enumerate(elements)}
        definitions = {e.get("id"):e for defs in self.root.iter() if local(defs.tag)=="defs" for e in defs.iter() if e.get("id")}
        node_list,text_list,connectors = [],[],[]
        root_matrix = np.eye(3)
        root_matrix[:2,2] = -np.asarray(self.origin)
        def visit(e,parent_matrix,in_defs=False):
            tag = local(e.tag)
            if in_defs or tag in {"defs","style","title","desc","metadata"}:
                return
            matrix = parent_matrix@transform(e.get("transform",""))
            s = scale(matrix)
            st = self.computed[e]
            if st.get("display") == "none" or st.get("visibility") != "visible":
                raise DiagramError("Hidden visible-tree elements are unsupported")
            if number(st.get("opacity","1"))<=0:
                raise DiagramError("Fully transparent visible-tree elements are unsupported")
            binding = Binding(indices[e],matrix,st)
            if tag=="rect":
                p = point(matrix,number(e.get("x"),0),number(e.get("y"),0))
                identifier = e.get("id",f"node-{len(node_list)}")
                n = Node(identifier,*p,number(e.get("width"))*s,number(e.get("height"))*s,fill=st["fill"],stroke=st["stroke"])
                node_list.append(n)
                self.nodes[identifier] = binding
            elif tag=="text":
                text_list.append((e,binding))
                return
            elif tag in {"line","polyline","path"}:
                if st.get("marker-end","none")=="none" or st.get("marker-start","none")!="none" or st.get("marker-mid","none")!="none":
                    raise DiagramError("Only singly directed connectors with marker-end are supported")
                marker = definitions.get(fragment_reference(st["marker-end"]))
                if marker is None or local(marker.tag)!="marker":
                    raise DiagramError("Connector marker-end does not resolve to a local marker definition")
                if st.get("stroke","none")=="none" or number(st.get("stroke-opacity","1"))<=0:
                    raise DiagramError("Invisible connector stroke")
                if tag!="line" and st.get("fill","black")!="none":
                    raise DiagramError("Connector paths and polylines require fill:none")
                if tag=="line":
                    pts = [point(matrix,number(e.get(f"x{i}"),0),number(e.get(f"y{i}"),0)) for i in [1,2]]
                elif tag=="polyline":
                    values = numbers(e.get("points",""))
                    if len(values)<4 or len(values)%2:
                        raise DiagramError("Invalid polyline points")
                    pts = [point(matrix,*values[i:i+2]) for i in range(0,len(values),2)]
                else:
                    pts = curve_points(e.get("d",""),matrix)
                identifier = e.get("id",f"edge-{len(connectors)}")
                connectors.append((identifier,pts))
                self.edges[identifier] = binding
            elif tag not in {"svg","g"}:
                raise DiagramError(f"Unsupported visible element: {tag}")
            for child in e:
                visit(child,matrix)
        visit(self.root,root_matrix)
        if not node_list:
            raise DiagramError("No supported rectangular nodes found")
        Diagram(width,height,node_list,[]).validate()
        for e,binding in text_list:
            st = binding.style
            if any(st.get(k,default)!=default for k,default in [("font-weight","normal"),("font-style","normal"),("letter-spacing","normal"),("word-spacing","normal")]):
                raise DiagramError("Only normal-weight, unspaced text is editable")
            family = st["font-family"].lower().replace('"','').replace("'","")
            if family.split(",")[0].strip() not in {"arial","liberation sans","dejavu sans","sans-serif"}:
                raise DiagramError("Editable text needs an explicit supported sans-serif font")
            children = list(e)
            if any(local(c.tag)!="tspan" or list(c) for c in children):
                raise DiagramError("Nested text markup is unsupported")
            if children and ((e.text or "").strip() or any((c.tail or "").strip() for c in children)):
                raise DiagramError("Mixed text and tspan content is unsupported")
            for c in children:
                if c.get("transform") or any(self.computed[c].get(k)!=st.get(k) for k in PROPERTIES):
                    raise DiagramError("Independently styled or transformed tspans are unsupported")
            anchor = children[0] if children and (e.get("x") is None or e.get("y") is None) else e
            p = point(binding.matrix,number(anchor.get("x",e.get("x"))),number(anchor.get("y",e.get("y"))))
            candidates = [n for n in node_list if n.x<=p[0]<=n.x+n.width and n.y<=p[1]<=n.y+n.height]
            if len(candidates)!=1:
                raise DiagramError(f"Text at {p} has {len(candidates)} possible owning nodes")
            n = candidates[0]
            if n.id in self.texts:
                raise DiagramError(f"Multiple text elements in {n.id}")
            n.lines = ["".join(c.itertext()) for c in children] if children else [e.text or ""]
            n.label = " ".join(n.lines)
            n.font_size = number(st["font-size"])*scale(binding.matrix)
            self.texts[n.id] = binding
        from .recovery import assemble
        recovered = assemble(width,height,node_list,connectors,[
            "Experimental source-bound SVG subset. Review recovered arrow ownership.",
            "Bezier recovery uses a 0.2 viewBox-unit subdivision tolerance; edits reroute connectors as straight segments.",
            "Checks cover box geometry and conservative sans-serif metrics, not pixel appearance or author intent."
        ],text,tolerance,attachment_model,attachment_overrides,review)
        self.review = recovered if review else None
        self.diagram = None if review else recovered

    def export(self,diagram):
        """Patch original elements; reject graph insertions until explicitly supported."""
        if self.diagram is None:
            raise DiagramError("An attachment review is not an accepted graph; apply decisions before editing")
        diagram.validate()
        if {n.id for n in diagram.nodes}!=set(self.nodes) or {e.id for e in diagram.edges}!=set(self.edges):
            raise DiagramError("Source-preserving export currently requires the original node and edge IDs; use normalized export for branch insertions")
        if diagram.to_dict()==self.diagram.to_dict():
            return self.text
        root = deepcopy(self.root)
        elements = list(root.iter())
        original_nodes = {n.id:n for n in self.diagram.nodes}
        def force(e,values):
            # Author !important outranks static stylesheet rules without deleting them.
            raw = e.get("style","").rstrip("; ")
            e.set("style",raw+(";" if raw else "")+";".join(f"{k}:{v} !important" for k,v in values.items()))
        if diagram.width!=self.diagram.width or diagram.height!=self.diagram.height:
            ox,oy = self.origin
            root.set("viewBox",f"{ox} {oy} {diagram.width} {diagram.height}")
            root.set("width",str(diagram.width))
            root.set("height",str(diagram.height))
        for n in diagram.nodes:
            binding = self.nodes[n.id]
            old = original_nodes[n.id]
            e = elements[binding.index]
            if any(getattr(n,k)!=getattr(old,k) for k in ["x","y","width","height"]):
                x,y = point(np.linalg.inv(binding.matrix),n.x,n.y)
                e.set("x",str(x)); e.set("y",str(y))
                e.set("width",str(n.width/scale(binding.matrix))); e.set("height",str(n.height/scale(binding.matrix)))
            if (n.x,n.y,n.width,n.height,n.label,n.font_size,n.lines)!=(old.x,old.y,old.width,old.height,old.label,old.font_size,old.lines):
                if n.id not in self.texts:
                    if n.label:
                        raise DiagramError("Cannot add text to an originally unlabeled node in source-preserving mode")
                    continue
                tb = self.texts[n.id]
                text = elements[tb.index]
                lines = n.lines or [n.label]
                y = n.y+n.height/2-(len(lines)-1)*n.font_size*.65+n.font_size*.33
                text.clear()
                # Keep source identity, classes, paint and metadata attributes.
                text.attrib.update(list(self.root.iter())[tb.index].attrib)
                force(text,{"font-size":f"{n.font_size/scale(tb.matrix)}px","text-anchor":"middle",
                            "dominant-baseline":"auto","alignment-baseline":"auto"})
                for attr in ["dx","dy"]:
                    text.attrib.pop(attr,None)
                for j,line in enumerate(lines):
                    x_local,y_local = point(np.linalg.inv(tb.matrix),n.x+n.width/2,y+j*n.font_size*1.3)
                    if j==0:
                        text.set("x",str(x_local)); text.set("y",str(y_local))
                    ET.SubElement(text,f"{{{NS}}}tspan",{"x":str(x_local),"y":str(y_local)}).text = line
        original_edges = {e.id:e for e in self.diagram.edges}
        for edge in diagram.edges:
            if edge.points==original_edges[edge.id].points:
                continue
            binding = self.edges[edge.id]
            e = elements[binding.index]
            inverse = np.linalg.inv(binding.matrix)
            pts = [point(inverse,*p) for p in edge.points]
            # Keep the tag so CSS tag selectors and DOM hierarchy retain meaning.
            tag = local(e.tag)
            if tag=="path":
                e.set("d"," ".join(f"{'M' if i==0 else 'L'} {x} {y}" for i,(x,y) in enumerate(pts)))
            elif tag=="polyline":
                e.set("points"," ".join(f"{x},{y}" for x,y in pts))
            elif len(pts)==2:
                for attr,v in zip(["x1","y1","x2","y2"],sum(pts,[])):
                    e.set(attr,str(v))
            else:
                raise DiagramError("A source line needs multiple routing segments; use normalized export or convert it to a path")
        ET.register_namespace("",NS)
        output = ET.tostring(root,encoding="unicode")
        # Recompute CSS after mutation to catch geometry-sensitive selector changes.
        changed_styles = styles(root)
        for binding in list(self.nodes.values())+list(self.edges.values())+list(self.texts.values()):
            current = changed_styles[elements[binding.index]]
            if any(current.get(k)!=binding.style.get(k) for k in PAINT):
                raise DiagramError("Edit changes computed source paint through a CSS selector; cannot preserve styling")
        return output
