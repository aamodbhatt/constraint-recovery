"""Fail-stop repeated-edit evaluation on authored programs with known graphs."""
import argparse
from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import time
import platform
import xml.etree.ElementTree as ET
from compare_elk import fixture,elk_layout
from constraint_recovery.model import DiagramError
from constraint_recovery.svg import render_svg,parse_svg
from constraint_recovery.layout import edit
from constraint_recovery.routing import OrthogonalRouter
from constraint_recovery.operations import add_branch
from constraint_recovery.check import verify
from constraint_recovery.conflicts import LayoutConflict,verify_certificate
from constraint_recovery.typography import wrap,text_width


ACTIONS = [
    {"name":"longer label","labels":{"n1":"Representation consistency verification"},"flow":"free"},
    {"name":"larger font","font_size":24,"flow":"free"},
    {"name":"portrait layout","width":320,"height":1700,"flow":"vertical"},
    {"name":"explicit branch","branch":["n1","review","Independent check"],"height":2000,"flow":"vertical"},
    {"name":"landscape layout","width":2000,"height":900,"flow":"horizontal"},
    {"name":"short label and smaller font","labels":{"n1":"Checked"},"font_size":18,"width":1400,"height":700,"flow":"horizontal"},
    {"name":"impossible canvas","width":80,"height":60,"flow":"horizontal","expected_rejection":True},
]


def save_demo(folder,name,svg,diagram):
    (folder/f"{name}.svg").write_text(svg)
    # A separate display crop removes blank canvas; the accepted SVG is intact.
    xs=[v for n in diagram.nodes for v in [n.x,n.x+n.width]]+[p[0] for e in diagram.edges for p in e.points]
    ys=[v for n in diagram.nodes for v in [n.y,n.y+n.height]]+[p[1] for e in diagram.edges for p in e.points]
    x,y=min(xs)-16,min(ys)-16
    width,height=max(xs)+16-x,max(ys)+16-y
    root=ET.fromstring(svg)
    root.set("viewBox",f"{x} {y} {width} {height}")
    root.set("width",str(width));root.set("height",str(height))
    (folder/f"{name}.preview.svg").write_text(ET.tostring(root,encoding="unicode")+"\n")


def initial(family,size):
    d=fixture(family,size)
    d.width,d.height=1200,900
    nodes={n.id:n for n in d.nodes}
    router=OrthogonalRouter(nodes,d.width,d.height)
    for edge in d.edges:
        edge.points,_=router.route(edge.source,edge.target)
    svg=render_svg(d)+"\n"
    actual=parse_svg(svg,tolerance=.01)
    check=verify(d,actual)
    if not check["passed"]:
        raise RuntimeError(f"Invalid shared source fixture: {check['errors']}")
    return svg,actual


def topological_strip(current,labels,width,height,font_size,flow):
    """Strong simple control: fitted nodes in one topological row or column."""
    d=deepcopy(current)
    d.width,d.height=width,height
    for n in d.nodes:
        n.label=labels.get(n.id,n.label)
        n.font_size=font_size
        n.lines=wrap(n.label,font_size,max(32,min(220,width-56,n.width-24)))
        n.width=max(n.width,max(text_width(s,font_size) for s in n.lines)+24)
        n.height=max(n.height,len(n.lines)*font_size*1.3+20)
    incoming={n.id:0 for n in d.nodes}
    outgoing={n.id:[] for n in d.nodes}
    for e in d.edges:
        incoming[e.target]+=1
        outgoing[e.source].append(e.target)
    pending=sorted(key for key,value in incoming.items() if value==0)
    order=[]
    while pending:
        u=pending.pop(0)
        order.append(u)
        for v in outgoing[u]:
            incoming[v]-=1
            if incoming[v]==0:
                pending.append(v);pending.sort()
    if len(order)!=len(d.nodes):
        raise DiagramError("Topological strip requires a DAG")
    by_id={n.id:n for n in d.nodes}
    horizontal=flow!="vertical"
    if flow=="free" and sum(n.width for n in d.nodes)+24*(len(d.nodes)-1)+32>width:
        horizontal=False
    position=16
    for key in order:
        n=by_id[key]
        n.x,n.y=(position,16) if horizontal else (16,position)
        position+=(n.width if horizontal else n.height)+24
    if any(n.x+n.width>width-16 or n.y+n.height>height-16 for n in d.nodes):
        raise DiagramError("Topological strip exceeds the requested canvas")
    router=OrthogonalRouter(by_id,width,height)
    for e in d.edges:
        e.points,_=router.route(e.source,e.target)
    return d,{"method":"Deterministic topological strip with common text fitting and visibility router"}


def run_sequence(family,size,method,node_binary="node",demo_dir=None):
    svg,state=initial(family,size)
    truth=deepcopy(state)
    minimum_font=16
    records=[]
    stopped=False
    demo=demo_dir is not None and family=="chain" and size==4 and method=="reuse"
    if demo:
        demo_dir.mkdir(parents=True,exist_ok=True)
        save_demo(demo_dir,"00-original",svg,state)
    for step,action in enumerate(ACTIONS,1):
        expected_rejection=action.get("expected_rejection",False)
        record={"step":step,"request":action,"expected_rejection":expected_rejection,"attempted":not stopped}
        if stopped:
            record.update(passed=False,skipped_reason="Prior feasible edit failed; no invalid state propagated")
            records.append(record)
            continue
        start=time.perf_counter()
        width=action.get("width",state.width)
        height=action.get("height",state.height)
        if action.get("font_size"):
            minimum_font=action["font_size"]
        labels=action.get("labels",{})
        for n in truth.nodes:
            n.label=labels.get(n.id,n.label)
        if action.get("branch"):
            truth=add_branch(truth,*action["branch"])
        try:
            incoming_hash=hashlib.sha256(svg.encode()).hexdigest()
            if method=="reuse":
                if state.source_sha256!=incoming_hash:
                    raise DiagramError("Stale constraint graph in sequence state")
                overrides={e.id:{"source":e.source,"target":e.target} for e in state.edges}
                current=parse_svg(svg,attachment_overrides=overrides)
            else:
                current=parse_svg(svg)
            before=deepcopy(current)
            if action.get("branch"):
                current=add_branch(current,*action["branch"])
            if method in {"reuse","fresh"}:
                result,metadata=edit(current,labels,width,height,action.get("font_size"),flow=action["flow"])
            elif method in {"elk","elk_repair"}:
                result,metadata=elk_layout(current,width,height,labels,minimum_font,
                    "DOWN" if action["flow"]=="vertical" else "RIGHT",node_binary)
                if method=="elk_repair":
                    result,repair=edit(result,width=width,height=height,flow=action["flow"])
                    metadata={"elk":metadata,"constraint_repair":repair,"method":"ELK initialization followed by the same MILP/routing repair engine"}
            elif method=="topological_strip":
                result,metadata=topological_strip(current,labels,width,height,minimum_font,action["flow"])
            else:
                result=deepcopy(current)
                result.width,result.height=width,height
                for n in result.nodes:
                    n.label=labels.get(n.id,n.label)
                    n.font_size=action.get("font_size",n.font_size)
                    if n.id in labels:
                        n.lines=[n.label]
                metadata={"method":"Direct label/font/canvas attribute changes; fixed node geometry and connector points"}
            output=render_svg(result)+"\n"
            actual=parse_svg(output,tolerance=.01)
            check=verify(truth,actual,minimum_font=minimum_font,flow=action["flow"],gap=24,
                         expected_canvas=(width,height))
            record.update(accepted=check["passed"],errors=check["errors"],metadata=metadata,
                          passed=not check["passed"] if expected_rejection else check["passed"],
                          input_sha256=incoming_hash,
                          graph_preserved={(e.id,e.source,e.target) for e in truth.edges}=={(e.id,e.source,e.target) for e in actual.edges})
            if check["passed"]:
                prior={n.id:n for n in before.nodes}
                record["displacement_l1"]=sum(abs(n.x-prior[n.id].x)+abs(n.y-prior[n.id].y) for n in actual.nodes if n.id in prior)
                record["output_sha256"]=actual.source_sha256
                state,svg=actual,output
                if demo:
                    save_demo(demo_dir,f"{step:02d}-edited",svg,state)
            elif not expected_rejection:
                stopped=True
        except (DiagramError,RuntimeError,subprocess.TimeoutExpired) as exc:
            record.update(accepted=False,passed=expected_rejection,errors=[str(exc)])
            if isinstance(exc,LayoutConflict):
                from constraint_recovery.model import Diagram
                record["conflict_witness_verified"]=verify_certificate(Diagram.from_dict(exc.fitted_diagram),exc.certificate,action["flow"])
                record["conflict_witness"]=exc.certificate
            if not expected_rejection:
                stopped=True
        record["seconds"]=time.perf_counter()-start
        records.append(record)
    return {"family":family,"initial_nodes":size,"method":method,"records":records,
            "completed_feasible_sequence":all(r["passed"] for r in records if not r["expected_rejection"]),
            "impossible_request_rejected":records[-1].get("attempted",False) and records[-1]["passed"]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--elk",action="store_true",help="Include the supplied-graph ELK baseline; requires npm ci")
    parser.add_argument("--node",default="node")
    parser.add_argument("--output",type=Path,default=Path("results/edit-sequences.json"))
    parser.add_argument("--demo-dir",type=Path)
    args=parser.parse_args()
    methods=["reuse","fresh","direct_attributes","topological_strip"]+(["elk","elk_repair"] if args.elk else [])
    cases=[("chain",4),("chain",6),("branch",4),("branch",6),("diamond",4)]
    sequences=[run_sequence(family,size,method,args.node,args.demo_dir) for family,size in cases for method in methods]
    summary={m:{"completed_feasible_sequences":sum(s["completed_feasible_sequence"] for s in sequences if s["method"]==m),
                "total_sequences":len(cases),"impossible_requests_rejected":sum(s["impossible_request_rejected"] for s in sequences if s["method"]==m),
                "feasible_steps_passed":sum(r["passed"] for s in sequences if s["method"]==m for r in s["records"] if not r["expected_rejection"]),
                "planned_feasible_steps":6*len(cases),
                "accepted_displacement_l1":sum(r.get("displacement_l1",0) for s in sequences if s["method"]==m for r in s["records"] if r.get("accepted"))} for m in methods}
    report={"schema_version":1,"task":"Repeated edits of authored synthetic SVG motifs with known program graphs", "summary":summary,"actions":ACTIONS,
            "environment":{"python":platform.python_version(),"numpy":version("numpy"),"scipy":version("scipy"),"Pillow":version("Pillow"),
                "elkjs":json.loads((Path(__file__).parents[1]/"node_modules/elkjs/package.json").read_text())["version"] if args.elk else None},
            "benchmark_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "protocol":"Same valid initial SVG and request order for every method. Fail-stop after a failed feasible request; skipped later requests remain visible. Only checked outputs become subsequent state. Final impossible request is expected to be rejected.",
            "limitations":["Small authored programs, not independently annotated external figures","Reuse and fresh recovery use the same layout engine; a tie does not demonstrate a reuse advantage",
                           "ELK receives the same recovered graph and fitted text but optimizes a different layout objective","Direct attributes is a simple fixed-geometry baseline, not a modern AI editor",
                           "ELK repair uses the same MILP engine; it is a hybrid baseline, not an independent solver",
                           "Topological strip shares the visibility router and text metrics; motifs can be easy for this baseline",
                           "Edge-edge crossings and actual browser typography are outside this benchmark"],"sequences":sequences}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    if args.demo_dir:
        (args.demo_dir/"sequence.json").write_text(json.dumps(next(s for s in sequences if s["method"]=="reuse" and s["family"]=="chain" and s["initial_nodes"]==4),indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    if any(not s["completed_feasible_sequence"] or not s["impossible_request_rejected"] for s in sequences if s["method"] in {"reuse","fresh"}):
        raise SystemExit(1)


if __name__=="__main__":
    main()
