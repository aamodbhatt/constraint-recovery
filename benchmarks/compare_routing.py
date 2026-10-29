"""Paired fixed-geometry routing checks with common eight-unit clearance."""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import time
from constraint_recovery.model import Node,Edge,Diagram,DiagramError
from constraint_recovery.routing import OrthogonalRouter
from constraint_recovery.layout import reroute
from constraint_recovery.svg import render_svg,parse_svg
from constraint_recovery.check import verify,segment_hits_rect


def cases():
    yield "straight",Diagram(600,300,[Node("a",20,100,60,60),Node("b",520,100,60,60)],[Edge("ab","a","b")])
    for count in [2,3,4,5,6]:
        width=220+110*count
        nodes=[Node("a",20,100,40,40,label="S",font_size=12,lines=["S"],fill="#dff4e8"),
               Node("b",width-80,100,40,40,label="T",font_size=12,lines=["T"],fill="#fff1ce")]
        for i in range(count):
            nodes.append(Node(f"barrier-{i}",130+110*i,0 if i%2==0 else 100,30,200))
        yield f"alternating-{count}",Diagram(width,300,nodes,[Edge("ab","a","b")])
    yield "blocked",Diagram(600,300,[Node("a",20,100,60,60),Node("b",520,100,60,60),Node("wall",250,0,30,300)],[Edge("ab","a","b")])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("results/routing-comparison.json"))
    parser.add_argument("--examples",type=Path,help="Optional directory for authored SVG demonstrations")
    args=parser.parse_args()
    records=[]
    for name,original in cases():
        for method in ["templates","visibility"]:
            d=deepcopy(original)
            nodes={n.id:n for n in d.nodes}
            start=time.perf_counter()
            result={"case":name,"method":method,"expected_feasible":name!="blocked"}
            try:
                if method=="visibility":
                    d.edges[0].points,evidence=OrthogonalRouter(nodes,d.width,d.height,clearance=8).route("a","b")
                    result["search"]=evidence
                else:
                    reroute(d.edges[0],nodes,d.width,d.height,clearance=8)
                serialized=render_svg(d)
                checked=verify(original,parse_svg(serialized,tolerance=.01))
                for j,(p,q) in enumerate(zip(d.edges[0].points,d.edges[0].points[1:])):
                    for n in d.nodes:
                        pad=0 if (n.id=="a" and j==0) or (n.id=="b" and j==len(d.edges[0].points)-2) else 8
                        box=replace(n,x=n.x-pad,y=n.y-pad,width=n.width+2*pad,height=n.height+2*pad)
                        if segment_hits_rect(p,q,box):
                            checked["errors"].append(f"Clearance check failed at {n.id}")
                checked["passed"]=not checked["errors"]
                result.update(passed=checked["passed"],errors=checked["errors"],length=sum(math.dist(p,q) for p,q in zip(d.edges[0].points,d.edges[0].points[1:])))
                if args.examples and method=="visibility" and name=="alternating-4":
                    args.examples.mkdir(parents=True,exist_ok=True)
                    (args.examples/"routing-maze.svg").write_text(serialized+"\n")
            except DiagramError as exc:
                result.update(passed=False,errors=[str(exc)])
            result["seconds"]=time.perf_counter()-start
            records.append(result)
    report={"scope":"Seven authored fixed-geometry cases; one deliberately blocked. No learned recovery or external figure accuracy tested.",
            "clearance":8,"shared_conditions":"Same nodes, center ports, canvas and eight-unit rectangle clearance; common post-serialization geometric checker. Source/target port escape segments may cross only their own inflated box.",
            "results":records,"limitations":["Small diagnostic cases selected to exercise route complexity, not a representative benchmark","Runtime is a local observation, not a speed claim","No edge-edge crossing avoidance, arrowhead bounds or stroke-width certification"]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({m:{"solved":sum(r["passed"] for r in records if r["method"]==m),"total":7} for m in ["templates","visibility"]},indent=2))
    if any(r["passed"]!=r["expected_feasible"] for r in records if r["method"]=="visibility"):
        raise SystemExit(1)


if __name__=="__main__":
    main()
