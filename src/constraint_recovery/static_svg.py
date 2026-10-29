"""Conservative static SVG source guard for geometry-preserving edits."""
import re
import xml.etree.ElementTree as ET
from defusedxml.ElementTree import DefusedXMLParser
from .model import DiagramError
from .svg import NS,local,guard_xml

TAGS={"svg","g","defs","marker","symbol","use","rect","circle","ellipse","line","polyline","polygon",
      "path","text","tspan","textPath","title","desc","metadata","style","linearGradient","radialGradient",
      "stop","pattern","image","clipPath","mask","filter","feDropShadow","feGaussianBlur","feOffset",
      "feBlend","feColorMatrix","feMerge","feMergeNode","feComposite","feFlood","feMorphology"}
URL_ATTRIBUTES={"fill","stroke","filter","clip-path","mask","marker-start","marker-mid","marker-end","cursor","color-profile"}
CSS_GEOMETRY={"transform","transform-origin","transform-box","d"}


def elements(root):
    result={}
    def visit(e,path):
        result[path]=e
        for i,child in enumerate(c for c in e if isinstance(c.tag,str)):
            visit(child,f"{path}/{local(child.tag)}[{i}]")
    visit(root,"svg")
    return result


def _css_tokens(tokens):
    for token in tokens:
        if token.type=="error":
            raise DiagramError("Malformed static SVG CSS")
        if token.type=="url":
            if not re.fullmatch(r"#[A-Za-z_][\w.:-]*",token.value):
                raise DiagramError("Static editing supports only same-document CSS URLs")
        if token.type=="function":
            if token.lower_name=="url":
                values=[v for v in token.arguments if v.type!="whitespace"]
                if len(values)!=1 or values[0].type!="string" or not re.fullmatch(r"#[A-Za-z_][\w.:-]*",values[0].value):
                    raise DiagramError("Static editing supports only same-document CSS URLs")
            else:
                _css_tokens(token.arguments)


def parse_static(source):
    if len(source.encode("utf-8"))>8_000_000:
        raise DiagramError("SVG source exceeds the eight-MB edit budget")
    guard_xml(source)
    try:
        parser=DefusedXMLParser(target=ET.TreeBuilder(insert_comments=True),forbid_dtd=True,forbid_entities=True,forbid_external=True)
        parser.feed(source)
        root=parser.close()
    except Exception as exc:
        raise DiagramError(f"Invalid or unsafe SVG XML: {exc}") from exc
    if root.tag!=f"{{{NS}}}svg":
        raise DiagramError("Compound editing requires an SVG namespace root")
    try:
        import tinycss2
    except ImportError as exc:
        raise DiagramError("Compound editing requires the SVG extra: pip install 'constraint-recovery[svg]'") from exc
    def declarations(raw):
        for declaration in tinycss2.parse_declaration_list(raw,skip_whitespace=True,skip_comments=True):
            if declaration.type!="declaration" or declaration.lower_name in CSS_GEOMETRY or declaration.lower_name.startswith(("animation","transition")):
                raise DiagramError("CSS transforms/path geometry, animations and malformed declarations are outside rigid-edit scope")
            _css_tokens(declaration.value)
    ids=set()
    for path,e in elements(root).items():
        tag=local(e.tag)
        if e.tag!=f"{{{NS}}}{tag}" or tag not in TAGS or (tag=="svg" and e is not root):
            raise DiagramError(f"Unsupported static edit element: {tag}")
        if e.get("id"):
            if e.get("id") in ids:
                raise DiagramError("Duplicate source SVG IDs")
            ids.add(e.get("id"))
        for key,value in e.attrib.items():
            name=local(key)
            if name.lower().startswith("on") or name in {"base","transform-origin","transform-box"}:
                raise DiagramError(f"Unsupported active or origin-dependent attribute: {name}")
            if name=="href":
                fragment=re.fullmatch(r"#[A-Za-z_][\w.:-]*",value.strip())
                raster=tag=="image" and re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=\s]+",value)
                if not fragment and not raster:
                    raise DiagramError("Editing requires local fragments or embedded raster images; external resources are unsupported")
            if name in URL_ATTRIBUTES:
                _css_tokens(tinycss2.parse_component_value_list(value))
        if e.get("style"):
            declarations(e.get("style"))
        if tag=="style":
            for rule in tinycss2.parse_stylesheet(e.text or "",skip_whitespace=True,skip_comments=True):
                if rule.type!="qualified-rule" or re.search(r":(?:hover|focus|active|visited|target)\b",tinycss2.serialize(rule.prelude),re.I):
                    raise DiagramError("Conditional/dynamic static-edit stylesheets are unsupported")
                declarations(rule.content)
    return root
