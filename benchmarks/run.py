"""Seeded synthetic engineering benchmark, not a learned-model or external-data result."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import statistics
import time
import sys
from constraint_recovery.model import Diagram, Node, Edge, DiagramError
from constraint_recovery.svg import parse_svg, render_svg, route
from constraint_recovery.layout import edit
from constraint_recovery.check import verify
from constraint_recovery.typography import wrap, text_width


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("artifacts/benchmark.json"))
    p.add_argument("--cases",type=int,default=30)
    args = p.parse_args()
    if args.cases < 1:
        p.error("--cases must be positive")
    rng = random.Random(20261029)
    records = []
    for i in range(args.cases):
        n = rng.randint(3,5)
        nodes = [Node(f"n{k}",24+k*190,80,150,60,f"Stage {k+1}") for k in range(n)]
        edges = [Edge(f"e{k}",nodes[k].id,nodes[k+1].id,route(nodes[k],nodes[k+1])) for k in range(n-1)]
        d = parse_svg(render_svg(Diagram(n*190+10,240,nodes,edges)))
        task = ["long-labels","larger-font","portrait"][i%3]
        labels = {f"n{k}":f"Stage {k+1} independent structural validation" for k in range(n)} if task=="long-labels" else {}
        width,height = (300,n*140+40) if task=="portrait" else (d.width,360)
        size = 24 if task=="larger-font" else 18
        # Simple declared baseline: fit text, scale positions to canvas, keep fixed node placements.
        base = deepcopy(d)
        base.width,base.height = width,height
        for node in base.nodes:
            node.x *= width/d.width
            node.y *= height/d.height
            node.label = labels.get(node.id,node.label)
            node.font_size = size
            node.lines = wrap(node.label,size,node.width-24)
            node.width = max(node.width,max(text_width(s,size) for s in node.lines)+24)
            node.height = max(node.height,len(node.lines)*size*1.3+20)
        lookup = {n.id:n for n in base.nodes}
        for e in base.edges:
            e.points = route(lookup[e.source],lookup[e.target])
        try:
            baseline = verify(d,parse_svg(render_svg(base)),labels,size)
        except DiagramError as exc:
            baseline = {"passed":False,"errors":[str(exc)]}
        started = time.perf_counter()
        error = None
        try:
            result,solver = edit(d,labels,width,height,size,flow="vertical" if task=="portrait" else "free")
            check = verify(d,parse_svg(render_svg(result),tolerance=.01),labels,size,
                           flow="vertical" if task=="portrait" else "free",gap=24)
        except DiagramError as exc:
            error = str(exc)
            check = {"passed":False,"errors":[error]}
        records.append({"case":i,"task":task,"nodes":n,"baseline_passed":baseline["passed"],
                        "baseline_errors":baseline["errors"],"solver_passed":check["passed"],
                        "seconds":time.perf_counter()-started,"errors":check["errors"]})
    report = {"seed":20261029,"cases":len(records),"kind":"synthetic engineering baseline",
              "baseline":"fixed placements, scaled positions, text fitting; not ELK or an LLM",
              "baseline_passes":sum(r["baseline_passed"] for r in records),
              "solver_passes":sum(r["solver_passed"] for r in records),
              "median_solver_seconds":statistics.median(r["seconds"] for r in records),
              "limitations":["Simple generated chains, not external SVGs", "No learned model", "No claim of research superiority"],"records":records}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2))
    return 0 if report["solver_passes"]==len(records) else 1


if __name__=="__main__":
    sys.exit(main())
