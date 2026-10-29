import argparse
import html
import json
from pathlib import Path
import sys
from .model import Diagram, DiagramError
from .svg import parse_svg, render_svg
from .layout import edit
from .check import verify


def main():
    parser = argparse.ArgumentParser(description="Recover and edit a supported SVG through explicit constraints.")
    commands = parser.add_subparsers(dest="command",required=True)
    witness = commands.add_parser("check-witness",help="Verify a saved layout conflict witness without running a solver")
    witness.add_argument("input",type=Path)
    inventory = commands.add_parser("inspect",help="Non-rendering primitive inventory; does not promise edit support")
    inventory.add_argument("input",type=Path)
    inventory.add_argument("--output",type=Path,required=True)
    recover = commands.add_parser("recover",help="Export the recovered graph for inspection")
    recover.add_argument("input",type=Path)
    recover.add_argument("--output",type=Path,required=True)
    review = commands.add_parser("review",help="Inspect ambiguous endpoint candidates in a portable local view")
    review.add_argument("input",type=Path)
    review.add_argument("--output",type=Path,required=True,help="Review observations JSON; an HTML view is written alongside")
    change = commands.add_parser("edit",help="Edit and independently validate the serialized SVG")
    change.add_argument("input",type=Path)
    change.add_argument("--output",type=Path,required=True)
    change.add_argument("--labels",type=Path,help="JSON object mapping node IDs to replacement labels")
    change.add_argument("--constraints",type=Path,help="Reviewed recovered graph, bound to input node/edge IDs")
    change.add_argument("--width",type=float)
    change.add_argument("--height",type=float)
    change.add_argument("--font-size",type=float)
    change.add_argument("--flow",choices=["free","vertical","horizontal"],default="free")
    change.add_argument("--router",choices=["visibility","candidates"],default="visibility")
    change.add_argument("--branch",nargs=3,action="append",metavar=("SOURCE","NEW_ID","LABEL"),
                        help="Add a labeled node and directed edge from an existing node; repeatable")
    for sub in [recover,change,review]:
        sub.add_argument("--endpoint-model",type=Path,help="Experimental synthetic-trained endpoint ranker JSON")
        sub.add_argument("--source-preserving",action="store_true",help="Opt-in static CSS/translation/uniform-scale/Bezier subset; patch original SVG elements")
        sub.add_argument("--attachments",type=Path,help="Source-hash-bound attachment choices exported by the review view")
    args = parser.parse_args()
    try:
        if args.command=="check-witness":
            from .conflicts import verify_certificate
            saved=json.loads(args.input.read_text())
            cert=saved["certificate"]
            verified=verify_certificate(Diagram.from_dict(saved["fitted_diagram"]),cert,
                                        cert.get("flow"),cert.get("gap"),cert.get("padding"))
            print(json.dumps({"verified":verified,"kind":cert.get("kind"),
                              "scope":"Arithmetic and referenced inequalities of the saved fitted graph; does not re-establish SVG recovery or author intent"},indent=2))
            return 0 if verified else 2
        destinations=[args.output]
        if args.command=="review":
            destinations.append(args.output.with_suffix(".html"))
        elif args.command=="edit":
            destinations.extend(args.output.with_suffix(suffix) for suffix in [".report.json",".constraints.json",".original.svg",".html",".failure.json"])
        if args.input.resolve() in {p.resolve() for p in destinations}:
            raise DiagramError("Output must differ from input; preserve the original SVG")
        if args.command=="inspect":
            from .inventory import inspect_svg
            inventory = inspect_svg(args.input.read_text())
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(inventory,indent=2)+"\n")
            print(json.dumps(inventory["summary"],indent=2))
            return 0
        model = None
        if args.endpoint_model:
            from .attachment import AttachmentModel
            model = AttachmentModel.load(args.endpoint_model)
        source_text=args.input.read_bytes().decode("utf-8")
        overrides=None
        if args.attachments:
            from .recovery import load_overrides
            overrides=load_overrides(json.loads(args.attachments.read_text()),source_text)
        document = None
        if args.source_preserving:
            from .source import SourceDocument
            document = SourceDocument(source_text,attachment_model=model,attachment_overrides=overrides,review=args.command=="review")
        original = (document.review if args.command=="review" else document.diagram) if document else parse_svg(source_text,attachment_model=model,attachment_overrides=overrides,review=args.command=="review")
        if args.command=="review":
            from .review import render_review
            if args.output.suffix.lower()!=".json":
                raise DiagramError("Review output must end in .json; the companion view uses .html")
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(original,indent=2)+"\n")
            args.output.with_suffix(".html").write_text(render_review(original))
            print(f"Review {len(original['connectors'])} arrows; {original['unresolved_endpoints']} endpoints need a choice. Open {args.output.with_suffix('.html')}")
            return 0
        if args.command=="recover":
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(original.to_dict(),indent=2)+"\n")
            print(f"Recovered {len(original.nodes)} nodes and {len(original.edges)} directed edges; review before use.")
            return 0
        declared = original
        if args.constraints:
            declared = Diagram.from_dict(json.loads(args.constraints.read_text()))
            for edge in declared.edges:
                if any(getattr(edge,role)!=value for role,value in (overrides or {}).get(edge.id,{}).items()):
                    raise DiagramError("Reviewed graph conflicts with explicit attachment choices")
            if {n.id for n in declared.nodes}!={n.id for n in original.nodes} or {e.id for e in declared.edges}!={e.id for e in original.edges}:
                raise DiagramError("Reviewed graph IDs do not match the source SVG")
            # Only relationship corrections are accepted; source geometry/text remains authoritative.
            declared = Diagram(original.width,original.height,original.nodes,declared.edges,original.warnings).validate()
        if args.branch:
            from .operations import add_branch
            for source,new_id,label in args.branch:
                declared = add_branch(declared,source,new_id,label)
        labels = json.loads(args.labels.read_text()) if args.labels else {}
        if not isinstance(labels,dict):
            raise DiagramError("Labels JSON must be an object")
        result,solver = edit(declared,labels,args.width,args.height,args.font_size,flow=args.flow,router=args.router)
        output = document.export(result) if document else render_svg(result)
        reparsed = SourceDocument(output,tolerance=.01).diagram if document else parse_svg(output,tolerance=.01)
        checks = verify(declared,reparsed,labels,args.font_size or 0,flow=args.flow,gap=24)
        if not checks["passed"]:
            raise DiagramError("Independent verification failed: "+"; ".join(checks["errors"]))
        report = {"verification":checks,"solver":solver,"warnings":result.warnings,
                  "requested_branch_insertions":args.branch or [],
                  "export_mode":"source-preserving" if document else "normalized",
                  "attachment_decisions":model.decisions if model else [],
                  "attachment_overrides":overrides or {},
                  "input":str(args.input),"node_count":len(result.nodes),"edge_count":len(result.edges)}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output+"\n")
        args.output.with_suffix(".report.json").write_text(json.dumps(report,indent=2)+"\n")
        args.output.with_suffix(".constraints.json").write_text(json.dumps(result.to_dict(),indent=2)+"\n")
        # Object embeds keep source SVG separate; report is local, with no remote scripts or assets.
        original_copy = args.output.with_suffix(".original.svg")
        original_copy.write_bytes(source_text.encode("utf-8"))
        source = html.escape(original_copy.name,quote=True)
        target = html.escape(args.output.name,quote=True)
        page = f'''<!doctype html><meta charset="utf-8"><title>Constraint recovery · verified edit</title>
<style>body{{font:16px system-ui;margin:40px;background:#f4f6fa;color:#172c47}}main{{max-width:1200px;margin:auto}}section{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}article{{background:white;padding:24px;border:1px solid #dbe3ee;border-radius:12px}}object{{width:100%;height:540px}}pre{{white-space:pre-wrap;font-size:13px}}small{{color:#586b83}}</style>
<main><small>LOCAL BASELINE · NO CLOUD INFERENCE</small><h1>Constraint recovery</h1>
<p>Accepted relationships and fitted geometry passed the independent checker.</p><section>
<article><h2>Original</h2><object data="{source}" type="image/svg+xml"></object></article>
<article><h2>Edited</h2><object data="{target}" type="image/svg+xml"></object></article></section>
<h2>Evidence and limitations</h2><pre>{html.escape(json.dumps(report,indent=2))}</pre></main>'''
        args.output.with_suffix(".html").write_text(page)
        print(json.dumps(report,indent=2))
        return 0
    except (DiagramError,OSError,ValueError,KeyError,TypeError) as exc:
        from .conflicts import LayoutConflict
        if isinstance(exc,LayoutConflict):
            failure=args.output.with_suffix(".failure.json")
            try:
                failure.parent.mkdir(parents=True,exist_ok=True)
                failure.write_text(json.dumps({"status":"infeasible","message":str(exc),"certificate":exc.certificate,
                                               "fitted_diagram":exc.fitted_diagram,"input":str(args.input)},indent=2)+"\n")
                print(f"Verified conflict witness: {failure}",file=sys.stderr)
            except OSError as output_error:
                print(f"Could not save conflict witness: {output_error}",file=sys.stderr)
        print(f"constraint-recovery: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
