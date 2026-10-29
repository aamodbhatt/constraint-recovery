"""Audit a predeclared prefix of an external dataset without redistributing SVGs."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import urllib.request
import ssl
from urllib.parse import urlencode
from constraint_recovery.model import DiagramError
from constraint_recovery.svg import parse_svg

DATASET = "yashengsun/SciDiagramRevision"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rows",type=int,default=20)
    p.add_argument("--output",type=Path,default=Path("results/external-compatibility.json"))
    p.add_argument("--ca-file",type=Path,help="Optional trusted CA bundle; TLS verification remains enabled")
    p.add_argument("--offset",type=int,default=0,help="Predeclare a contiguous split range before inspecting results")
    p.add_argument("--cache-dir",type=Path,help="Private local response cache; source SVGs must not be committed")
    p.add_argument("--offline",action="store_true",help="Require cached responses; make no network requests")
    p.add_argument("--extended",action="store_true",help="Also test the opt-in source-preserving importer")
    p.add_argument("--inventory",action="store_true",help="Record aggregate source syntax/geometry observations, without redistributing artwork")
    args = p.parse_args()
    if not 1 <= args.rows <= 100:
        p.error("--rows must be between 1 and 100")
    if args.offset<0 or args.offset+args.rows>1000:
        p.error("Requested range must be within the first 1000 rows")
    if args.offline and not args.cache_dir:
        p.error("--offline requires --cache-dir")
    records = []
    for offset in range(args.offset,args.offset+args.rows,5):
        length = min(5,args.offset+args.rows-offset)
        url = "https://datasets-server.huggingface.co/rows?"+urlencode({"dataset":DATASET,"config":"default","split":"test","offset":offset,"length":length})
        cache = args.cache_dir/f"SciDiagramRevision-test-{offset:04d}-{length}.json" if args.cache_dir else None
        if cache and cache.exists():
            raw = cache.read_bytes()
        else:
            if args.offline:
                raise RuntimeError(f"Missing private cache: {cache}")
            context = ssl.create_default_context(cafile=str(args.ca_file) if args.ca_file else None)
            with urllib.request.urlopen(url,timeout=60,context=context) as response:
                raw = response.read(24_000_001)
        if len(raw)>24_000_000:
            raise RuntimeError("Response exceeds the bounded audit download")
        payload = json.loads(raw)
        if [r.get("row_idx") for r in payload.get("rows",[])] != list(range(offset,offset+length)):
            raise RuntimeError("Unexpected row count; do not silently change the sample")
        if cache and not cache.exists():
            cache.parent.mkdir(parents=True,exist_ok=True)
            cache.write_bytes(raw)
        for item in payload["rows"]:
            row = item["row"]
            svg = row.get("input_svg")
            record = {"row":item["row_idx"],"task_id":row["task_id"],
                      "svg_sha256":hashlib.sha256(svg.encode()).hexdigest() if isinstance(svg,str) else None,
                      "svg_bytes":len(svg.encode()) if isinstance(svg,str) else 0,
                      "annotation_status":"not annotated; compatibility only"}
            if not isinstance(svg,str):
                record.update(supported=False,first_failure="Source SVG unavailable in dataset row")
                records.append(record)
                continue
            if "input_svg" in item.get("truncated_cells",[]):
                record.update(supported=False,first_failure="Dataset viewer truncated source SVG; not parsed")
                records.append(record)
                continue
            try:
                d = parse_svg(svg)
                record.update(supported=True,nodes=len(d.nodes),edges=len(d.edges),first_failure=None)
            except DiagramError as exc:
                record.update(supported=False,first_failure=str(exc))
            if args.extended:
                from constraint_recovery.source import SourceDocument
                try:
                    d = SourceDocument(svg).diagram
                    record["source_preserving"] = {"supported":True,"nodes":len(d.nodes),"edges":len(d.edges),"first_failure":None}
                except DiagramError as exc:
                    record["source_preserving"] = {"supported":False,"first_failure":str(exc)}
            if args.inventory:
                from constraint_recovery.inventory import inspect_svg
                try:
                    inventory = inspect_svg(svg)
                    record["inventory"] = {k:inventory[k] for k in ["all_element_counts","reference_counts","active_content_signals","summary"]}
                except DiagramError as exc:
                    record["inventory"] = {"failure":str(exc)}
            records.append(record)
    report = {"dataset":DATASET,"source":"https://huggingface.co/datasets/"+DATASET,
              "selection":f"Contiguous published test rows {args.offset}..{args.offset+args.rows-1}; not a representative random sample",
              "license":"mixed-arxiv-source; no source SVGs or images redistributed",
              "rows":len(records),"supported":sum(r["supported"] for r in records),
              "first_failure_counts":dict(collections.Counter(r["first_failure"] for r in records if not r["supported"])),
              "limitations":["Not an edit-quality evaluation", "Only first parser failure recorded", "No ground-truth relationship annotations"],
              "records":records}
    if args.extended:
        extended = [r.get("source_preserving",{"supported":False,"first_failure":r["first_failure"]}) for r in records]
        report["source_preserving"] = {"supported":sum(r["supported"] for r in extended),
            "first_failure_counts":dict(collections.Counter(r["first_failure"] for r in extended if not r["supported"]))}
    if args.inventory:
        inventories = [r["inventory"] for r in records if "inventory" in r and "failure" not in r["inventory"]]
        tags = collections.Counter()
        stats = collections.Counter()
        for item in inventories:
            tags.update(item["summary"]["visible_tags"])
            stats.update({k:v for k,v in item["summary"].items() if k!="visible_tags"})
        report["inventory"] = {"inventoried_sources":len(inventories),"visible_tag_counts":dict(tags),
            "aggregate_observations":dict(stats),"interpretation":"Source syntax/geometry observations only; not node/edge labels or editing coverage"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2))


if __name__=="__main__":
    main()
