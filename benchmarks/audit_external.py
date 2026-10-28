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
    args = p.parse_args()
    if not 1 <= args.rows <= 100:
        p.error("--rows must be between 1 and 100")
    records = []
    for offset in range(0,args.rows,5):
        url = "https://datasets-server.huggingface.co/rows?"+urlencode({"dataset":DATASET,"config":"default","split":"test","offset":offset,"length":min(5,args.rows-offset)})
        context = ssl.create_default_context(cafile=str(args.ca_file) if args.ca_file else None)
        with urllib.request.urlopen(url,timeout=60,context=context) as response:
            raw = response.read(24_000_001)
        if len(raw)>24_000_000:
            raise RuntimeError("Response exceeds the bounded audit download")
        payload = json.loads(raw)
        if len(payload.get("rows",[])) != min(5,args.rows-offset):
            raise RuntimeError("Unexpected row count; do not silently change the sample")
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
            records.append(record)
    report = {"dataset":DATASET,"source":"https://huggingface.co/datasets/"+DATASET,
              "selection":"First N rows in published test split order; not a representative random sample",
              "license":"mixed-arxiv-source; no source SVGs or images redistributed",
              "rows":len(records),"supported":sum(r["supported"] for r in records),
              "first_failure_counts":dict(collections.Counter(r["first_failure"] for r in records if not r["supported"])),
              "limitations":["Not an edit-quality evaluation", "Only first parser failure recorded", "No ground-truth relationship annotations"],
              "records":records}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="records"},indent=2))


if __name__=="__main__":
    main()
