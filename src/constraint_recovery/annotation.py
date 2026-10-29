"""Source-bound compound-object annotations; no inferred labels or gold claims."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re
from defusedxml import ElementTree as SafeET
from .model import DiagramError
from .svg import guard_xml,local,NS

ROLES={"node","container","connector","text","background","decoration","unknown"}
RELATIONS={"directed_edge","contains","group","align_x","align_y","before_x","before_y"}
STATUSES={"confirmed","ambiguous","unknown"}


def validate_annotation(data,source_sha256=None,measurements=None):
    if not isinstance(data,dict) or data.get("schema_version")!=2 or data.get("kind")!="diagram-annotation":
        raise DiagramError("Unsupported diagram annotation schema")
    digest=data.get("source_sha256")
    if not isinstance(digest,str) or not re.fullmatch(r"[0-9a-f]{64}",digest):
        raise DiagramError("Invalid annotation source digest")
    if source_sha256 is not None and digest!=source_sha256:
        raise DiagramError("Annotation belongs to a different SVG")
    for key in ["diagram_id","source_url","license"]:
        if not isinstance(data.get(key),str) or not data[key].strip():
            raise DiagramError(f"Annotation needs {key}")
    if data.get("split") not in {"train","development","test","unassigned"}:
        raise DiagramError("Invalid annotation split")
    review=data.get("review")
    if not isinstance(review,dict) or review.get("status") not in {"unreviewed","agent-reviewed","human-reviewed"} or review.get("annotator_type") not in {"unspecified","agent","human"}:
        raise DiagramError("Invalid annotation review metadata")
    if any(not isinstance(review.get(k),str) for k in ["annotator","evidence"]):
        raise DiagramError("Review identity/evidence must be text")
    if review["status"]!="unreviewed":
        expected="human" if review["status"]=="human-reviewed" else "agent"
        if review["annotator_type"]!=expected or not review["annotator"].strip() or not review["evidence"].strip():
            raise DiagramError("Reviewed annotations need consistent annotator type, identity and evidence")
    objects,relations=data.get("objects"),data.get("relations")
    if not isinstance(objects,list) or not isinstance(relations,list):
        raise DiagramError("Annotation objects and relations must be arrays")
    known=None
    if measurements is not None:
        if not isinstance(measurements,dict):
            raise DiagramError("Measurements must be an object")
        if measurements.get("source_sha256")!=digest:
            raise DiagramError("Geometry measurements belong to a different SVG")
        inventory=measurements.get("primitives")
        if not isinstance(inventory,list) or any(not isinstance(p,dict) or not isinstance(p.get("location"),str) for p in inventory):
            raise DiagramError("Invalid measured primitive inventory")
        known={p["location"]:p for p in inventory}
        if len(known)!=len(inventory):
            raise DiagramError("Duplicate primitive locations in measurements")
    ids,parts=set(),set()
    for obj in objects:
        if not isinstance(obj,dict):
            raise DiagramError("Invalid annotation object")
        identifier=obj.get("id")
        if not isinstance(identifier,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*",identifier) or identifier in ids:
            raise DiagramError("Annotation object IDs must be unique identifiers")
        ids.add(identifier)
        if obj.get("role") not in ROLES or obj.get("status") not in STATUSES or not isinstance(obj.get("name"),str):
            raise DiagramError(f"Invalid role/status/name: {identifier}")
        members=obj.get("parts")
        if not isinstance(members,list) or not members or any(not isinstance(p,str) for p in members) or len(set(members))!=len(members) or parts.intersection(members):
            raise DiagramError("Primitive parts must be nonempty, unique and disjoint across objects")
        if known is not None and set(members)-set(known):
            raise DiagramError("Unknown primitive part in annotation")
        geometry=obj.get('connector_geometry')
        if geometry is not None:
            if not isinstance(geometry,dict) or obj['role']!='connector' or geometry.get('direction')!='forward' or geometry.get('shaft') not in members or set(geometry)-{'shaft','direction','end_head'}:
                raise DiagramError("Connector geometry requires a member shaft and explicit forward source-path direction")
            head=geometry.get('end_head')
            expected={geometry['shaft']}
            if head is not None:
                if not isinstance(head,dict) or set(head)!={'part','tip'} or head.get('part') not in members or head['part']==geometry['shaft']:
                    raise DiagramError("Invalid separate connector head member")
                tip=head.get('tip')
                if not isinstance(tip,list) or len(tip)!=2 or any(type(v) not in {int,float} or not math.isfinite(v) for v in tip):
                    raise DiagramError("Connector head tip requires two finite local SVG coordinates")
                expected.add(head['part'])
            if set(members)!=expected:
                raise DiagramError("Connector geometry does not cover exactly its shaft and optional end head")
        parts.update(members)
    for relation in relations:
        if not isinstance(relation,dict) or relation.get("kind") not in RELATIONS or relation.get("status") not in STATUSES or not isinstance(relation.get("rationale"),str):
            raise DiagramError("Invalid annotated relation")
        targets=relation.get("objects")
        if not isinstance(targets,list) or len(targets)<2 or any(not isinstance(p,str) or p not in ids for p in targets):
            raise DiagramError("Relation references unknown annotation objects")
        if relation["kind"]!="group" and len(targets)!=2:
            raise DiagramError("This relation requires exactly two objects")
        if relation.get("connector") is not None and (not isinstance(relation["connector"],str) or relation["connector"] not in ids):
            raise DiagramError("Relation references an unknown connector object")
    coverage=data.get("coverage")
    if not isinstance(coverage,dict) or type(coverage.get("total_primitives")) is not int or coverage["total_primitives"]<0 or type(coverage.get("assigned_primitives")) is not int or coverage.get("assigned_primitives")!=len(parts):
        raise DiagramError("Annotation coverage does not match assigned primitive parts")
    unassigned=coverage.get("unassigned_parts")
    if not isinstance(unassigned,list) or any(not isinstance(p,str) for p in unassigned) or len(set(unassigned))!=len(unassigned) or parts.intersection(unassigned):
        raise DiagramError("Invalid unassigned primitive coverage")
    if len(parts)+len(unassigned)!=coverage["total_primitives"]:
        raise DiagramError("Annotation coverage denominator is inconsistent")
    if known is not None and parts|set(unassigned)!=set(known):
        raise DiagramError("Annotation does not account for the measured primitive inventory")
    return {"valid":True,"objects":len(objects),"relations":len(relations),"assigned_primitives":len(parts),
            "total_primitives":coverage["total_primitives"],"review_status":review["status"],
            "source_match_checked":source_sha256 is not None,"primitive_inventory_checked":known is not None,
            "scope":"Structure, provenance and references only; no independent verification of annotation truth or annotator identity"}


def annotation_page(source,measurements,diagram_id,source_url,license_name):
    if len(source.encode("utf-8"))>8_000_000:
        raise DiagramError("Annotation source exceeds eight MB")
    if not all(isinstance(v,str) and v.strip() for v in [diagram_id,source_url,license_name]):
        raise DiagramError("Annotation source metadata must be nonempty")
    guard_xml(source)
    try:
        root=SafeET.fromstring(source)
    except Exception as exc:
        raise DiagramError(f"Invalid SVG for annotation: {exc}") from exc
    if root.tag!=f"{{{NS}}}svg":
        raise DiagramError("Expected SVG annotation input")
    digest=hashlib.sha256(source.encode("utf-8")).hexdigest()
    if not isinstance(measurements,dict) or measurements.get("schema_version")!=1 or measurements.get("source_sha256")!=digest:
        raise DiagramError("Geometry measurements do not match this source SVG")
    if measurements.get("root_css_transform","none")!="none":
        raise DiagramError("Annotation image projection currently excludes root CSS transforms")
    try:
        import tinycss2
    except ImportError as exc:
        raise DiagramError("Annotation requires the 'svg' extra") from exc
    def static_declarations(raw):
        for d in tinycss2.parse_declaration_list(raw,skip_whitespace=True,skip_comments=True):
            if d.type!="declaration" or d.lower_name.startswith(("animation","transition")):
                raise DiagramError("Dynamic or malformed annotation stylesheet")
    for e in root.iter():
        if local(e.tag) in {"animate","animateMotion","animateTransform","set","discard"}:
            raise DiagramError("Animated SVGs need a separately frozen source before annotation")
        if local(e.tag)=="style":
            for rule in tinycss2.parse_stylesheet(e.text or "",skip_whitespace=True,skip_comments=True):
                if rule.type!="qualified-rule" or re.search(r":(?:hover|focus|active|visited|target)\b",tinycss2.serialize(rule.prelude),re.I):
                    raise DiagramError("Conditional/dynamic annotation stylesheets are unsupported")
                static_declarations(rule.content)
        if e.get("style"):
            static_declarations(e.get("style"))
    image_size=measurements.get("image_size",[])
    projection=measurements.get("image_projection",[])
    if len(image_size)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<v<=20000 for v in image_size) or len(projection)!=6 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in projection):
        raise DiagramError("Missing or invalid browser image projection; rerun geometry measurement")
    primitives=measurements.get("primitives")
    if not isinstance(primitives,list) or not primitives or len(primitives)>5000:
        raise DiagramError("Annotation needs a bounded measured primitive inventory")
    locations=set()
    for p in primitives:
        if not isinstance(p,dict) or not isinstance(p.get("location"),str) or p["location"] in locations:
            raise DiagramError("Primitive source locations must be unique")
        locations.add(p["location"])
        b=p.get("viewbox_bounds")
        if b is not None and (len(b)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in b) or b[0]>b[2] or b[1]>b[3]):
            raise DiagramError("Invalid measured primitive envelope")
    payload={"source_sha256":digest,"diagram_id":diagram_id,"source_url":source_url,"license":license_name,
             "image_size":image_size,"image_projection":projection,
             "browser":measurements.get("browser"),"blocked_references":len(measurements.get("blocked_references",[])),
             "primitives":[{k:p[k] for k in ["location","source_id","tag","viewbox_bounds","visible_by_display_visibility_opacity"]} for p in primitives]}
    template=(Path(__file__).parent/"assets/annotation.html").read_text()
    image_url="data:image/svg+xml;base64,"+base64.b64encode(source.encode("utf-8")).decode("ascii")
    return template.replace("__IMAGE_URL__",image_url,1).replace("__DATA_JSON__",json.dumps(payload).replace("<","\\u003c"),1)
