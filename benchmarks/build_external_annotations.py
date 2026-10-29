"""Build private, unlabelled annotation views for an offline development range."""
import argparse
import hashlib
import json
from pathlib import Path
from constraint_recovery.annotation import annotation_page
from constraint_recovery.model import DiagramError


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--rows",type=int,default=20)
    parser.add_argument("--offset",type=int,default=0)
    parser.add_argument("--cache-dir",type=Path,default=Path(".cache/external"))
    parser.add_argument("--measurements",type=Path,default=Path(".cache/browser-geometry"))
    parser.add_argument("--views",type=Path,default=Path(".cache/annotation-views"))
    parser.add_argument("--output",type=Path,default=Path("results/annotation-view-audit.json"))
    args=parser.parse_args()
    if not 1<=args.rows<=100 or args.offset<0:
        parser.error("Choose a predeclared nonnegative range of at most 100 rows")
    if ".cache" not in args.views.resolve().parts:
        parser.error("External source/view copies must stay in a private .cache directory")
    rows={}
    for file in sorted(args.cache_dir.glob("SciDiagramRevision-test-*.json")):
        for item in json.loads(file.read_text())["rows"]:
            index=item["row_idx"]
            if args.offset<=index<args.offset+args.rows:
                if index in rows and rows[index]["row"].get("input_svg")!=item["row"].get("input_svg"):
                    raise RuntimeError("Conflicting cached source rows")
                rows[index]=item
    if set(rows)!=set(range(args.offset,args.offset+args.rows)):
        raise RuntimeError("Private cache does not cover the full predeclared range")
    args.views.mkdir(parents=True,exist_ok=True)
    records=[]
    for index,item in sorted(rows.items()):
        row=item["row"];source=row.get("input_svg")
        record={"row":index,"task_id":row["task_id"],"source_sha256":hashlib.sha256(source.encode()).hexdigest() if isinstance(source,str) else None}
        if not isinstance(source,str) or "input_svg" in item.get("truncated_cells",[]):
            record.update(built=False,failure="Unavailable or truncated source")
            records.append(record)
            continue
        try:
            measured=json.loads((args.measurements/f"row-{index:04d}.json").read_text())
            page=annotation_page(source,measured,row["task_id"],"https://huggingface.co/datasets/yashengsun/SciDiagramRevision","mixed-arxiv-source")
            (args.views/f"row-{index:04d}.html").write_text(page,encoding="utf-8")
            (args.views/f"row-{index:04d}.source.svg").write_bytes(source.encode("utf-8"))
            record.update(built=True,failure=None,primitives=len(measured["primitives"]),blocked_references=len(measured.get("blocked_references",[])))
        except (DiagramError,OSError,ValueError,KeyError,TypeError) as exc:
            record.update(built=False,failure=str(exc))
        records.append(record)
    blocked=sum(r.get("blocked_references",0) for r in records)
    report={"schema_version":1,"dataset":"yashengsun/SciDiagramRevision",
            "selection":f"Published test rows {args.offset}..{args.offset+args.rows-1}, used here for development audit; not an untouched evaluation set",
            "requested_rows":args.rows,"views_built":sum(r["built"] for r in records),"annotations_created":0,
            "secondary_references_blocked":blocked,
            "protocol":"Offline private source/measurement cache. Views start with no object or relation labels. All HTML and original SVG copies stay in ignored .cache; only build outcomes and source hashes committed.",
            "limitations":["A built view is not a completed annotation, rendering-fidelity certificate or editable figure",
                           f"{blocked} secondary references in this range were blocked during measurement; affected views retain that warning",
                           "No independent human annotation or relationship accuracy is established","Upstream figure rights remain per source paper"],
            "records":records}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in {"records","limitations","protocol"}},indent=2))


if __name__=="__main__":
    main()
