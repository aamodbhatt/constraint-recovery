"""Reviewed rigid-object edits and an independent browser-measurement checker."""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import numpy as np
from .annotation import validate_annotation
from .check import segment_hits_rect
from .geometry import numbers,transform,point
from .model import Node,DiagramError
from .routing import OrthogonalRouter
from .static_svg import parse_static,elements
from .svg import NS,local

EPS=.05


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_digest(data):
    return digest(json.dumps(data,sort_keys=True,separators=(",",":")))


def affine(values):
    if not isinstance(values,list) or len(values)!=6 or not all(type(v) in {int,float} and math.isfinite(v) for v in values):
        raise DiagramError("Missing finite browser affine matrix")
    a,b,c,d,e,f=values
    return np.array([[a,c,e],[b,d,f],[0,0,1]],dtype=float)


def union(boxes):
    if not boxes or any(b is None for b in boxes):
        raise DiagramError("Object has unmeasured geometry")
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]


def shifted(box,delta):
    return [box[0]+delta[0],box[1]+delta[1],box[2]+delta[0],box[3]+delta[1]]


def overlaps(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>EPS and min(a[3],b[3])-max(a[1],b[1])>EPS


def contains(a,b):
    return a[0]<=b[0]+EPS and a[1]<=b[1]+EPS and a[2]>=b[2]-EPS and a[3]>=b[3]-EPS


def box_node(identifier,box):
    return Node(identifier,box[0],box[1],max(box[2]-box[0],.001),max(box[3]-box[1],.001))


def accepted_annotation(manifest,source_hash,measurements):
    if not isinstance(manifest,dict):
        raise DiagramError("Compound manifest must be an object")
    if manifest.get("kind")=="compound-constraints":
        if manifest.get("schema_version")!=1 or manifest.get("source_sha256")!=source_hash:
            raise DiagramError("Compound constraint state belongs to a different source")
        annotation=manifest.get("annotation")
        if not isinstance(annotation,dict) or manifest.get("annotation_sha256")!=json_digest(annotation):
            raise DiagramError("Compound state annotation snapshot does not match its digest")
        history=manifest.get("history")
        if not isinstance(history,list) or not history:
            raise DiagramError("Compound constraint state needs a provenance history")
        expected=annotation.get("source_sha256")
        for item in history:
            if not isinstance(item,dict) or item.get("input_sha256")!=expected or not re.fullmatch(r"[0-9a-f]{64}",str(item.get("output_sha256",""))):
                raise DiagramError("Broken compound constraint provenance chain")
            expected=item["output_sha256"]
        if expected!=source_hash:
            raise DiagramError("Compound state history does not end at this source")
        validate_annotation(annotation)
        current={**annotation,"source_sha256":source_hash}
        validate_annotation(current,source_hash,measurements)
    else:
        annotation=manifest
        validate_annotation(annotation,source_hash,measurements)
    if annotation["review"]["status"]=="unreviewed":
        raise DiagramError("Compound edits require explicitly reviewed assumptions; unreviewed annotations cannot authorize movement")
    return annotation


def measured_parts(source,measurements):
    if measurements.get("source_sha256")!=digest(source) or measurements.get("javascript_enabled") is not False or measurements.get("network_enabled") is not False:
        raise DiagramError("Source-bound offline browser measurements required")
    if measurements.get("blocked_references"):
        raise DiagramError("Missing secondary resources prevent a source-preserving compound edit")
    if not isinstance(measurements.get("document_styles"),dict):
        raise DiagramError("Full descendant/definition style measurements required")
    result={}
    for p in measurements.get("primitives",[]):
        if p.get("viewbox_bounds") is None or not isinstance(p.get("computed_all"),dict):
            raise DiagramError("Compound editing needs complete geometry and --style-details measurements")
        if p.get("has_unbounded_effects"):
            raise DiagramError("Filter, mask and clipping extents are not supported by this compound adapter")
        if p["location"] in result:
            raise DiagramError("Duplicate measured primitive locations")
        affine(p.get("matrix"));affine(p.get("parent_matrix"))
        result[p["location"]]=p
    if not result:
        raise DiagramError("No measured SVG primitives")
    return result


class CompoundDocument:
    def __init__(self,source,measurements,manifest):
        self.source=source
        self.root=parse_static(source)
        self.elements=elements(self.root)
        self.measurements=measurements
        self.parts=measured_parts(source,measurements)
        self.annotation=accepted_annotation(manifest,digest(source),measurements)
        self.objects={o["id"]:o for o in self.annotation["objects"]}
        self.boxes={key:union([self.parts[p]["viewbox_bounds"] for p in obj["parts"]]) for key,obj in self.objects.items()}
        self.owner={p:key for key,obj in self.objects.items() for p in obj["parts"]}
        self.edges=[]
        for relation in self.annotation["relations"]:
            if relation["kind"]=="directed_edge" and relation["status"]=="confirmed":
                connector=relation.get("connector")
                if connector is None or connector not in self.objects or self.objects[connector]["role"]!="connector":
                    raise DiagramError("Confirmed edges need an explicit connector object")
                if any(e["connector"]==connector for e in self.edges):
                    raise DiagramError("A connector object cannot represent multiple edges")
                self.edges.append(relation)
        for location,p in self.parts.items():
            e=self.elements.get(location)
            if e is None or local(e.tag)!=p["tag"] or e.get("id")!=p.get("source_id"):
                raise DiagramError("Measured primitive locations/IDs do not match the source DOM")
            marker=p["computed_all"].get("marker-end","none")
            if marker!="none" and not any(location in self.objects[r["connector"]]["parts"] for r in self.edges):
                raise DiagramError("Every marked arrow needs a confirmed connector relationship before movement")

    def deltas(self,moves):
        if not isinstance(moves,dict) or not moves:
            raise DiagramError("Moves must be a nonempty object mapping object IDs to [dx,dy]")
        result={key:[0.,0.] for key in self.objects}
        for key,delta in moves.items():
            if key not in self.objects or not isinstance(delta,list) or len(delta)!=2 or not all(type(v) in {int,float} and math.isfinite(v) for v in delta):
                raise DiagramError("Invalid compound move ID or finite translation")
            obj=self.objects[key]
            if obj["role"]!="node" or obj["status"]!="confirmed":
                raise DiagramError("Only confirmed node objects can move; containers and unresolved objects are protected")
            if min(self.boxes[key][2]-self.boxes[key][0],self.boxes[key][3]-self.boxes[key][1])<=0:
                raise DiagramError("Movable compound nodes need positive measured extents")
            result[key]=[float(v) for v in delta]
        return result

    def ancestors(self,key):
        result=set()
        while True:
            extra={r["objects"][0] for r in self.annotation["relations"] if r["kind"]=="contains" and r["status"]=="confirmed" and r["objects"][1] in result|{key}}
            if extra<=result:
                break
            result|=extra
            if key in result:
                raise DiagramError("Containment cycle cannot define a compound edit region")
        return result

    def obstacles(self,boxes,endpoints=()):
        ancestors=set().union(*(self.ancestors(key) for key in endpoints)) if endpoints else set()
        obstacles={}
        for key,obj in self.objects.items():
            if obj["role"] in {"background","connector"}:
                continue
            if obj["role"]=="container" and key in ancestors:
                children=[self.boxes[r["objects"][1]] for r in self.annotation["relations"] if r["kind"]=="contains" and r["status"]=="confirmed" and r["objects"][0]==key]
                for location in obj["parts"]:
                    box=self.parts[location]["viewbox_bounds"]
                    if not any(contains(box,child) for child in children):
                        obstacles["part:"+location]=box
            else:
                obstacles[key]=boxes[key]
        for location,p in self.parts.items():
            if location not in self.owner:
                obstacles["part:"+location]=p["viewbox_bounds"]
        return obstacles

    def check_positions(self,deltas):
        boxes={key:shifted(box,deltas[key]) for key,box in self.boxes.items()}
        width,height=self.measurements["canvas"]
        for key,delta in deltas.items():
            if delta==[0.,0.]:
                continue
            box=boxes[key]
            if box[0]<-EPS or box[1]<-EPS or box[2]>width+EPS or box[3]>height+EPS:
                raise DiagramError(f"Moved compound node outside canvas: {key}")
            for parent in self.ancestors(key):
                if self.objects[parent]["role"]!="container":
                    raise DiagramError("Contains relations need explicit container objects")
                frames=[self.parts[p]["viewbox_bounds"] for p in self.objects[parent]["parts"] if contains(self.parts[p]["viewbox_bounds"],self.boxes[key])]
                if not contains(boxes[parent],box) or any(not contains(frame,box) for frame in frames):
                    raise DiagramError(f"Move leaves declared container: {parent} contains {key}")
            for other,obstacle in self.obstacles(boxes,(key,)).items():
                if other!=key and overlaps(box,obstacle):
                    raise DiagramError(f"Moved node overlaps protected object/envelope: {key}, {other}")
        for relation in self.annotation["relations"]:
            ids=relation["objects"]
            if not any(deltas[key]!=[0.,0.] for key in ids):
                continue
            if relation["status"]!="confirmed":
                raise DiagramError("An uncertain relation touches a moved object; review it before editing")
            kind=relation["kind"]
            if kind in {"align_x","align_y","group"}:
                axes=[0] if kind=="align_x" else [1] if kind=="align_y" else [0,1]
                if any(abs(deltas[key][axis]-deltas[ids[0]][axis])>1e-7 for key in ids for axis in axes):
                    raise DiagramError(f"Move changes the declared {kind} relationship")
            if kind in {"before_x","before_y"}:
                axis=0 if kind=="before_x" else 1
                centers=[(boxes[key][axis]+boxes[key][axis+2])/2 for key in ids]
                if centers[0]>centers[1]+EPS:
                    raise DiagramError(f"Move reverses declared {kind} order")
        return boxes

    def connector(self,relation):
        obj=self.objects[relation["connector"]]
        if obj["status"]!="confirmed" or len(obj["parts"])!=1:
            raise DiagramError("Rerouting currently needs a confirmed single-primitive connector; arrow-label groups are not yet supported")
        location=obj["parts"][0]
        p=self.parts[location]
        style=p["computed_all"]
        if p["tag"] not in {"path","polyline","line"} or "path_geometry" not in p or style.get("marker-end","none")=="none" or style.get("marker-start","none")!="none" or style.get("marker-mid","none")!="none":
            raise DiagramError("Rerouting requires a singly marked line, polyline or open path")
        if p["tag"]!="line" and style.get("fill")!="none":
            raise DiagramError("Connector paths require fill:none")
        if math.dist(p["path_geometry"]["start"],p["path_geometry"]["end"])<1e-6:
            raise DiagramError("Closed/degenerate connector paths are unsupported")
        return location,p


def portals(box,anchor,outward,clearance=8):
    if len(anchor)!=2 or len(outward)!=2 or not all(math.isfinite(v) for v in [*anchor,*outward]) or math.hypot(*outward)<1e-8:
        raise DiagramError("Connector needs a nondegenerate measured endpoint direction")
    if not contains([box[0]-8,box[1]-8,box[2]+8,box[3]+8],[*anchor,*anchor]):
        raise DiagramError("Reviewed connector endpoint is too far from its compound node envelope")
    largest=max(abs(v) for v in outward)
    result=[]
    for axis,value in enumerate(outward):
        if abs(value)+1e-6<largest:
            continue
        stub=list(anchor)
        stub[axis]=max(box[axis+2]+clearance,anchor[axis]+clearance) if value>0 else min(box[axis]-clearance,anchor[axis]-clearance)
        result.append((list(anchor),stub,axis))
    return result


def prepare(source,measurements,manifest,moves):
    document=CompoundDocument(source,measurements,manifest)
    deltas=document.deltas(moves)
    boxes=document.check_positions(deltas)
    root=deepcopy(document.root)
    mapped=elements(root)
    allowed={}
    moved_parts={}
    for key,delta in deltas.items():
        if delta==[0.,0.]:
            continue
        for location in document.objects[key]["parts"]:
            p=document.parts[location]
            parent=affine(p["parent_matrix"])
            if abs(np.linalg.det(parent[:2,:2]))<1e-8:
                raise DiagramError("Singular parent transforms cannot support a rigid compound move")
            translation=np.eye(3);translation[:2,2]=delta
            local_matrix=transform(mapped[location].get("transform",""),allow_affine=True)
            result=np.linalg.inv(parent)@translation@parent@local_matrix
            a,c,e=result[0];b,d,f=result[1]
            mapped[location].set("transform",f"matrix({a:.15g} {b:.15g} {c:.15g} {d:.15g} {e:.15g} {f:.15g})")
            allowed[location]=["transform"]
            moved_parts[location]=delta
    rerouted=[]
    for relation in document.edges:
        start,end=relation["objects"]
        if deltas[start]==[0.,0.] and deltas[end]==[0.,0.]:
            continue
        if start==end or document.objects[start]["role"]!="node" or document.objects[end]["role"]!="node":
            raise DiagramError("Affected edges require two distinct node objects")
        location,p=document.connector(relation)
        geometry=p["path_geometry"]
        source_anchor=np.add(geometry["start"],deltas[start]).tolist()
        target_anchor=np.add(geometry["end"],deltas[end]).tolist()
        source_ports=portals(boxes[start],source_anchor,geometry["start_direction"])
        target_ports=portals(boxes[end],target_anchor,[-v for v in geometry["end_direction"]])
        obstacles=document.obstacles(boxes,(start,end))
        obstacles[start],obstacles[end]=boxes[start],boxes[end]
        router=OrthogonalRouter({key:box_node(key,b) for key,b in obstacles.items()},*measurements["canvas"],
                                extra_points=[v[1] for v in source_ports+target_ports])
        points,evidence=router.route(start,end,source_ports,target_ports)
        inverse=np.linalg.inv(affine(p["matrix"]))
        local_points=[point(inverse,*v) for v in points]
        e=mapped[location]
        if p["tag"]=="path":
            e.set("d"," ".join(f"{'M' if i==0 else 'L'} {x:.15g} {y:.15g}" for i,(x,y) in enumerate(local_points)))
            allowed[location]=["d"]
        elif p["tag"]=="polyline":
            e.set("points"," ".join(f"{x:.15g},{y:.15g}" for x,y in local_points))
            allowed[location]=["points"]
        elif len(local_points)==2:
            for name,value in zip(["x1","y1","x2","y2"],sum(local_points,[])):
                e.set(name,f"{value:.15g}")
            allowed[location]=["x1","y1","x2","y2"]
        else:
            raise DiagramError("The source line needs bends; changing its SVG tag could change CSS, so this edit is declined")
        rerouted.append({"location":location,"connector":relation["connector"],"source":start,"target":end,
                         "source_anchor":source_anchor,"target_anchor":target_anchor,"routing":evidence})
    ET.register_namespace("",NS)
    output=ET.tostring(root,encoding="unicode")+"\n" if allowed else source
    return output,{"schema_version":1,"input_sha256":digest(source),"output_sha256":digest(output),"moves":moves,
                   "allowed_attributes":allowed,"moved_parts":moved_parts,"rerouted":rerouted,
                   "annotation_sha256":json_digest(document.annotation)}


def _same(a,b,tolerance=EPS):
    return np.asarray(a).shape==np.asarray(b).shape and np.isfinite(a).all() and np.isfinite(b).all() and np.max(np.abs(np.asarray(a)-np.asarray(b)),initial=0)<=tolerance


def _tree_snapshot(e,allowed,path="svg"):
    attrs={k:v for k,v in e.attrib.items() if k not in allowed.get(path,set())}
    children=[]
    index=0
    for raw_index,child in enumerate(e):
        if isinstance(child.tag,str):
            child_path=f"{path}/{local(child.tag)}[{index}]";index+=1
        else:
            child_path=f"{path}/#comment[{raw_index}]"
        children.append(_tree_snapshot(child,allowed,child_path))
    return e.tag if isinstance(e.tag,str) else "#comment",attrs,e.text,e.tail,tuple(children)


def _polyline(e,matrix):
    tag=local(e.tag)
    if tag=="line":
        pts=[[float(e.get("x1","0")),float(e.get("y1","0"))],[float(e.get("x2","0")),float(e.get("y2","0"))]]
    elif tag=="polyline":
        raw=numbers(e.get("points",""))
        if len(raw)<4 or len(raw)%2:
            raise DiagramError("Invalid serialized connector points")
        pts=[raw[i:i+2] for i in range(0,len(raw),2)]
    else:
        raw=e.get("d","")
        tokens=re.findall(r"[ML]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",raw)
        if re.sub(r"[ML]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?","",raw).strip(" ,\t\n\r") or len(tokens)<6 or len(tokens)%3 or tokens[0]!="M":
            raise DiagramError("Verified reroutes must serialize as explicit M/L segments")
        pts=[]
        for i in range(0,len(tokens),3):
            if tokens[i]!=("M" if i==0 else "L"):
                raise DiagramError("Disconnected serialized reroute")
            pts.append([float(tokens[i+1]),float(tokens[i+2])])
    return [point(matrix,*p) for p in pts]


def verify_compound(source,before,manifest,moves,candidate,after):
    """Check requested world translations and protected source state; no router call."""
    document=CompoundDocument(source,before,manifest)
    deltas=document.deltas(moves)
    boxes=document.check_positions(deltas)
    after_parts=measured_parts(candidate,after)
    if set(after_parts)!=set(document.parts):
        raise DiagramError("Serialized primitive identity set changed")
    for key in ["canvas","origin","image_size","image_projection"]:
        if not _same(before[key],after[key]):
            raise DiagramError(f"Serialized source viewport changed: {key}")
    root=parse_static(candidate)
    new_elements=elements(root)
    if set(document.elements)!=set(new_elements):
        raise DiagramError("Source element hierarchy changed")
    moved={p:delta for key,delta in deltas.items() if delta!=[0.,0.] for p in document.objects[key]["parts"]}
    rerouted={}
    for edge in document.edges:
        if any(deltas[key]!=[0.,0.] for key in edge["objects"]):
            location,p=document.connector(edge)
            rerouted[location]=edge
    allowed_changes={}
    for location,old in document.elements.items():
        allowed={"transform"} if location in moved else {"d"} if location in rerouted and local(old.tag)=="path" else {"points"} if location in rerouted and local(old.tag)=="polyline" else {"x1","y1","x2","y2"} if location in rerouted else set()
        allowed_changes[location]=allowed
    if _tree_snapshot(document.root,allowed_changes)!=_tree_snapshot(root,allowed_changes):
        raise DiagramError("Protected source hierarchy, attributes, text or comments changed")
    if set(before["document_styles"])!=set(after["document_styles"]):
        raise DiagramError("Measured document style identity set changed")
    for location,old in before["document_styles"].items():
        ignored={"transform"} if location in moved else {"d"} if location in rerouted and document.parts[location]["tag"]=="path" else set()
        if {k:v for k,v in old.items() if k not in ignored}!={k:v for k,v in after["document_styles"][location].items() if k not in ignored}:
            raise DiagramError(f"Computed source/descendant/definition styling changed: {location}")
    for location,old in document.parts.items():
        new=after_parts[location]
        if (old["tag"],old.get("source_id"))!=(new["tag"],new.get("source_id")):
            raise DiagramError("Source primitive tags or IDs changed")
        ignored={"transform"} if location in moved else {"d"} if location in rerouted and old["tag"]=="path" else set()
        if {k:v for k,v in old["computed_all"].items() if k not in ignored}!={k:v for k,v in new["computed_all"].items() if k not in ignored}:
            raise DiagramError(f"Computed source styling changed: {location}")
        if old["visible_by_display_visibility_opacity"]!=new["visible_by_display_visibility_opacity"]:
            raise DiagramError("Source visibility changed")
        if location not in rerouted:
            delta=moved.get(location,[0.,0.])
            if not _same(new["viewbox_bounds"],shifted(old["viewbox_bounds"],delta)):
                raise DiagramError(f"Browser envelope failed the rigid/protected pose check: {location}")
            expected=affine(old["matrix"]);expected[:2,2]+=delta
            if not _same(affine(new["matrix"]),expected):
                raise DiagramError(f"Browser transform changed local shape or relative pose: {location}")
    for location,edge in rerouted.items():
        start,end=edge["objects"]
        p=document.parts[location];new=after_parts[location]
        for role,key in [("start",start),("end",end)]:
            expected=np.add(p["path_geometry"][role],deltas[key]).tolist()
            if not _same(new["path_geometry"][role],expected):
                raise DiagramError("Rerouted connector detached from its original relative anchor")
        points=_polyline(new_elements[location],affine(new["matrix"]))
        width,height=after["canvas"]
        if any(x<-EPS or y<-EPS or x>width+EPS or y>height+EPS for x,y in points):
            raise DiagramError("Rerouted connector outside canvas")
        for j,(p,q) in enumerate(zip(points,points[1:])):
            for key,box in document.obstacles(boxes,(start,end)).items():
                if (key==start and j==0) or (key==end and j==len(points)-2):
                    continue
                if segment_hits_rect(p,q,box_node(key,box)):
                    raise DiagramError(f"Reroute crosses a protected/node envelope: {key}")
    # Unchanged arrows must not be covered by a newly moved unrelated node.
    for edge in document.edges:
        location,p=document.connector(edge)
        if location in rerouted:
            continue
        for key,delta in deltas.items():
            if delta!=[0.,0.] and key not in edge["objects"] and overlaps(boxes[key],p["viewbox_bounds"]):
                raise DiagramError("Moved node could cover an unchanged connector; its conservative envelope overlaps")
    return {"passed":True,"moved_objects":sum(delta!=[0.,0.] for delta in deltas.values()),"moved_primitives":len(moved),
            "rerouted_connectors":len(rerouted),"protected_primitives":len(document.parts)-len(moved)-len(rerouted),
            "tolerance_viewbox_units":EPS,"input_sha256":digest(source),"output_sha256":digest(candidate),
            "annotation_sha256":json_digest(document.annotation),"accepted_review":document.annotation["review"],
            "scope":"Checks source hierarchy/text/attributes, computed styles, rigid affine poses, declared relationships and connector anchors/envelopes. Does not prove author intent, pixel identity, or stroke/marker collision bounds."}


def next_state(manifest,report,moves):
    annotation=manifest["annotation"] if manifest.get("kind")=="compound-constraints" else manifest
    history=list(manifest.get("history",[])) if manifest.get("kind")=="compound-constraints" else []
    history.append({"input_sha256":report["input_sha256"],"output_sha256":report["output_sha256"],"moves":moves})
    return {"schema_version":1,"kind":"compound-constraints","source_sha256":report["output_sha256"],
            "annotation":annotation,"annotation_sha256":json_digest(annotation),"history":history,
            "scope":"Derived editing state inherits accepted assumptions; original annotation and review provenance remain unchanged. This is not a newly human-reviewed annotation."}


def main():
    parser=argparse.ArgumentParser(description="Internal compound-edit preparation/verification worker")
    parser.add_argument("action",choices=["prepare","verify"])
    for name in ["source","measurements","manifest","moves"]:
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--after",type=Path)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--state",type=Path)
    args=parser.parse_args()
    try:
        source=args.source.read_bytes().decode("utf-8")
        before=json.loads(args.measurements.read_text());manifest=json.loads(args.manifest.read_text());moves=json.loads(args.moves.read_text())
        if args.action=="prepare":
            output,report=prepare(source,before,manifest,moves)
            args.candidate.write_bytes(output.encode("utf-8"))
        else:
            if not args.after or not args.state:
                raise DiagramError("Verification requires after measurements and state destination")
            report=verify_compound(source,before,manifest,moves,args.candidate.read_bytes().decode("utf-8"),json.loads(args.after.read_text()))
            args.state.write_text(json.dumps(next_state(manifest,report,moves),indent=2)+"\n")
        args.report.write_text(json.dumps(report,indent=2)+"\n")
        return 0
    except (DiagramError,ValueError,TypeError,KeyError,OSError,np.linalg.LinAlgError) as exc:
        print(f"compound-edit: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
