import argparse
import html
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from .model import Diagram, DiagramError
from .svg import parse_svg, render_svg
from .layout import edit
from .check import verify


def main():
    parser = argparse.ArgumentParser(description="Recover and edit a supported SVG through explicit constraints.")
    commands = parser.add_subparsers(dest="command",required=True)
    compound=commands.add_parser("edit-compound",help="Browser-verify rigid moves of explicitly reviewed compound objects")
    compound.add_argument("input",type=Path)
    manifests=compound.add_mutually_exclusive_group(required=True)
    manifests.add_argument("--annotation",type=Path)
    manifests.add_argument("--constraints",type=Path)
    compound.add_argument("--moves",type=Path,required=True,help="JSON object mapping node object IDs to [dx,dy] in viewBox units")
    compound.add_argument("--output",type=Path,required=True)
    compound.add_argument("--node",default="node")
    compound.add_argument('--routing',choices=['channel','visibility'],default='channel',help='Prefer ordered channel tracks for supported parallel groups, otherwise use visibility routing')
    agreement=commands.add_parser('compare-annotations',help='Compare two source-bound annotations without choosing a gold reviewer')
    agreement.add_argument('left',type=Path)
    agreement.add_argument('right',type=Path)
    agreement.add_argument('--source',type=Path,help='Optional exact source SVG to verify both hashes')
    agreement.add_argument('--measurements',type=Path,help='Optional browser primitive inventory to validate both records')
    agreement.add_argument('--output',type=Path,required=True)
    agreement.add_argument('--html',action='store_true',help='Also write a portable adjudication HTML beside the JSON; source overlays require --source and --measurements')
    witness = commands.add_parser("check-witness",help="Verify a saved layout conflict witness without running a solver")
    witness.add_argument("input",type=Path)
    validate_annotation = commands.add_parser("check-annotation",help="Validate annotation structure, source binding and primitive references")
    validate_annotation.add_argument("input",type=Path)
    validate_annotation.add_argument("--source",type=Path)
    validate_annotation.add_argument("--measurements",type=Path)
    annotate = commands.add_parser("annotate",help="Build a local compound-object annotation view without model suggestions")
    annotate.add_argument("input",type=Path)
    annotate.add_argument("--measurements",type=Path,required=True,help="JSON from benchmarks/measure_svg.cjs")
    annotate.add_argument("--output",type=Path,required=True,help="Local HTML containing the source image; keep external figures private")
    annotate.add_argument("--diagram-id")
    annotate.add_argument("--source-url")
    annotate.add_argument("--license",default="unknown")
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
        if args.command=='compare-annotations':
            from .agreement import compare_annotations
            inputs=[args.left,args.right,*([args.source] if args.source else []),*([args.measurements] if args.measurements else [])]
            outputs=[args.output,*([args.output.with_suffix('.html')] if args.html else [])]
            if any(p.resolve() in {v.resolve() for v in inputs} for p in outputs):
                raise DiagramError('Comparison output must not overwrite source, annotation or measurement files')
            if args.html and args.output.suffix.lower()!='.json':
                raise DiagramError('HTML comparison needs a .json output path')
            left=json.loads(args.left.read_text());right=json.loads(args.right.read_text())
            source=args.source.read_bytes().decode('utf-8') if args.source else None
            measured=json.loads(args.measurements.read_text()) if args.measurements else None
            result=compare_annotations(left,right,source,measured)
            page=None
            if args.html:
                from .agreement_view import comparison_page
                page=comparison_page(result,left,right,source,measured)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
            if page is not None:args.output.with_suffix('.html').write_text(page)
            print(json.dumps({key:result[key] for key in ['coverage','roles','grouping']},indent=2))
            return 0
        if args.command=="edit-compound":
            if args.output.suffix.lower()!=".svg":
                raise DiagramError("Compound output must end in .svg")
            manifest=args.annotation or args.constraints
            inputs={p.resolve() for p in [args.input,manifest,args.moves]}
            targets=[args.output,*[args.output.with_suffix(s) for s in [".report.json",".compound.json",".measurements.json"]]]
            if inputs.intersection(p.resolve() for p in targets):
                raise DiagramError("Compound output artifacts must not overwrite source or request files")
            request={"input":str(args.input.resolve()),"manifest":str(manifest.resolve()),"moves":str(args.moves.resolve()),
                     "output":str(args.output.resolve()),"python":sys.executable,"routing":args.routing}
            call=subprocess.run([args.node,str(Path(__file__).parent/"assets/compound_edit.cjs")],input=json.dumps(request),
                                text=True,capture_output=True,timeout=90)
            if call.returncode:
                raise DiagramError((call.stderr or call.stdout).strip())
            print(call.stdout.strip())
            return 0
        if args.command=="check-annotation":
            from .annotation import validate_annotation
            digest=hashlib.sha256(args.source.read_bytes()).hexdigest() if args.source else None
            measurements=json.loads(args.measurements.read_text()) if args.measurements else None
            result=validate_annotation(json.loads(args.input.read_text()),digest,measurements)
            print(json.dumps(result,indent=2))
            return 0
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
        if args.command=="annotate":
            from .annotation import annotation_page
            if args.output.suffix.lower()!=".html":
                raise DiagramError("Annotation view output must end in .html")
            page=annotation_page(args.input.read_bytes().decode("utf-8"),json.loads(args.measurements.read_text()),
                                 args.diagram_id or args.input.stem,args.source_url or args.input.name,args.license)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(page,encoding="utf-8")
            print(f"Local annotation view: {args.output}. No annotations or human review claims created.")
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
        reviewed=None
        effective_overrides=overrides
        if args.command=="edit" and args.constraints:
            reviewed=Diagram.from_dict(json.loads(args.constraints.read_text()))
            if reviewed.source_sha256 and reviewed.source_sha256!=hashlib.sha256(source_text.encode("utf-8")).hexdigest():
                raise DiagramError("Reviewed constraint graph belongs to a different source SVG")
            effective_overrides={edge.id:{"source":edge.source,"target":edge.target} for edge in reviewed.edges}
            for key,values in (overrides or {}).items():
                if key not in effective_overrides or any(effective_overrides[key].get(role)!=value for role,value in values.items()):
                    raise DiagramError("Reviewed graph conflicts with explicit attachment choices")
        document = None
        if args.source_preserving:
            from .source import SourceDocument
            document = SourceDocument(source_text,attachment_model=model,attachment_overrides=effective_overrides,review=args.command=="review")
        original = (document.review if args.command=="review" else document.diagram) if document else parse_svg(source_text,attachment_model=model,attachment_overrides=effective_overrides,review=args.command=="review")
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
            declared = reviewed
            if {n.id for n in declared.nodes}!={n.id for n in original.nodes} or {e.id for e in declared.edges}!={e.id for e in original.edges}:
                raise DiagramError("Reviewed graph IDs do not match the source SVG")
            # Only relationship corrections are accepted; source geometry/text remains authoritative.
            warnings=list(original.warnings)
            if not declared.source_sha256:
                warnings.append("Legacy constraint graph has no source hash; only node/edge IDs were checked")
            declared = Diagram(original.width,original.height,original.nodes,declared.edges,warnings,
                               source_sha256=original.source_sha256).validate()
        if args.branch:
            from .operations import add_branch
            for source,new_id,label in args.branch:
                declared = add_branch(declared,source,new_id,label)
        labels = json.loads(args.labels.read_text()) if args.labels else {}
        if not isinstance(labels,dict):
            raise DiagramError("Labels JSON must be an object")
        result,solver = edit(declared,labels,args.width,args.height,args.font_size,flow=args.flow,router=args.router)
        output = document.export(result) if document else render_svg(result)
        if not output.endswith("\n"):
            output+="\n"
        reparsed = SourceDocument(output,tolerance=.01).diagram if document else parse_svg(output,tolerance=.01)
        checks = verify(declared,reparsed,labels,args.font_size or 0,flow=args.flow,gap=24,
                        expected_canvas=(result.width,result.height))
        if not checks["passed"]:
            raise DiagramError("Independent verification failed: "+"; ".join(checks["errors"]))
        result.source_sha256=hashlib.sha256(output.encode("utf-8")).hexdigest()
        report = {"verification":checks,"solver":solver,"warnings":result.warnings,
                  "input_sha256":original.source_sha256,"output_sha256":result.source_sha256,
                  "requested_branch_insertions":args.branch or [],
                  "export_mode":"source-preserving" if document else "normalized",
                  "attachment_decisions":model.decisions if model else [],
                  "attachment_overrides":overrides or {},
                  "reviewed_constraint_graph":str(args.constraints) if args.constraints else None,
                  "input":str(args.input),"node_count":len(result.nodes),"edge_count":len(result.edges)}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(output.encode("utf-8"))
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
    except (DiagramError,OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
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
