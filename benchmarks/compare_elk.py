"""Compare layout only: equal graph, fitted text and canvas budget for both engines."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import time
from constraint_recovery.model import Diagram, DiagramError, Edge, Node
from constraint_recovery.svg import render_svg,parse_svg,route
from constraint_recovery.layout import edit
from constraint_recovery.typography import wrap,text_width
from constraint_recovery.check import verify

HERE = Path(__file__).resolve().parent


def fixture(family,size):
    nodes = [Node(f"n{k}",30+(k%3)*210,50+(k//3)*150,150,64,f"Stage {k+1}") for k in range(size)]
    pairs = [(k,k+1) for k in range(size-1)] if family=="chain" else [(0,k) for k in range(1,size)]
    if family=="diamond":
        pairs = [(0,1),(0,2),(1,3),(2,3)]
    edges = [Edge(f"e{k}",nodes[a].id,nodes[b].id,route(nodes[a],nodes[b])) for k,(a,b) in enumerate(pairs)]
    return Diagram(700,600,nodes,edges).validate()


def elk_layout(d,width,height,labels,font_size,direction,node_binary):
    result = deepcopy(d)
    result.width,result.height = width,height
    for n in result.nodes:
        n.label = labels.get(n.id,n.label)
        n.font_size = font_size
        n.lines = wrap(n.label,font_size,max(32,min(220,width-56,n.width-24)))
        n.width = max(n.width,max(text_width(s,font_size) for s in n.lines)+24)
        n.height = max(n.height,len(n.lines)*font_size*1.3+20)
    request = {"nodes":[n.__dict__ for n in result.nodes],"edges":[e.__dict__ for e in result.edges],"direction":direction}
    call = subprocess.run([node_binary,str(HERE/"elk_layout.cjs")],input=json.dumps(request),text=True,capture_output=True,timeout=30)
    if call.returncode:
        raise RuntimeError(call.stderr)
    graph = json.loads(call.stdout)
    positions = {n["id"]:n for n in graph["children"]}
    for n in result.nodes:
        n.x,n.y = positions[n.id]["x"],positions[n.id]["y"]
    edges = {e["id"]:e for e in graph["edges"]}
    for e in result.edges:
        section = edges[e.id]["sections"][0]
        points = [section["startPoint"],*section.get("bendPoints",[]),section["endPoint"]]
        e.points = [[p["x"],p["y"]] for p in points]
    return result,{"natural_width":graph["width"],"natural_height":graph["height"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--node",default="node")
    p.add_argument("--output",type=Path,default=Path("results/elk-comparison.json"))
    args = p.parse_args()
    records = []
    for family in ["chain","branch","diamond"]:
        for size in ([4] if family=="diamond" else [4,6]):
            original = fixture(family,size)
            for mode,width,height in [("wide",1100,500),("portrait",380,1200),("tight",300,260)]:
                labels = {n.id:f"Stage {k+1} validation process" for k,n in enumerate(original.nodes)}
                for method in ["milp","elk"]:
                    start = time.perf_counter()
                    try:
                        if method=="milp":
                            result,meta = edit(original,labels,width,height,20,flow="vertical" if mode=="portrait" else "free")
                        else:
                            result,meta = elk_layout(original,width,height,labels,20,"DOWN" if mode=="portrait" else "RIGHT",args.node)
                        actual = parse_svg(render_svg(result),tolerance=.01)
                        check = verify(original,actual,labels,20,flow="vertical" if mode=="portrait" else "free",gap=24)
                        displacement = sum(abs(a.x-b.x)+abs(a.y-b.y) for a,b in zip(original.nodes,result.nodes))
                    except DiagramError as exc:
                        check = {"passed":False,"errors":[str(exc)]}
                        displacement,meta = None,{}
                    records.append({"family":family,"nodes":size,"canvas":mode,"method":method,
                                    "passed":check["passed"],"errors":check["errors"],"displacement_l1":displacement,
                                    "seconds":time.perf_counter()-start,"layout_metadata":meta})
    report = {"task":"Layout only with identical supplied graph and fitted text",
              "elk_version":json.loads((HERE.parent/"node_modules/elkjs/package.json").read_text())["version"],
              "limitations":["Generated motifs, not a real-diagram or relation-inference evaluation",
                             "MILP optimizes displacement; ELK optimizes layered layout with the declared direction",
                             "Both checked against fixed canvas; ELK natural extents are reported without scaling fonts",
                             "ELK timing includes starting a Node process; no inference-speed claim"],
              "passes":{m:sum(r["passed"] for r in records if r["method"]==m) for m in ["milp","elk"]},
              "records":records}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2))


if __name__=="__main__":
    main()
