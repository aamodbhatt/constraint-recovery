from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from constraint_recovery.annotation import annotation_page,validate_annotation
from constraint_recovery.model import DiagramError
from constraint_recovery.cli import main

SOURCE='''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="150">
<rect id="a" x="20" y="20" width="80" height="60"/><text x="40" y="50">A</text>
<rect id="b" x="180" y="20" width="80" height="60"/><text x="210" y="50">B</text>
<path d="M100 50L180 50"/></svg>'''
PARTS=[f"svg/{tag}[{i}]" for i,tag in enumerate(["rect","text","rect","text","path"])]
DIGEST=hashlib.sha256(SOURCE.encode()).hexdigest()


def measurements():
    return {"schema_version":1,"source_sha256":DIGEST,"browser":"test fixture","image_size":[300,150],
            "image_projection":[1,0,0,1,0,0],"root_css_transform":"none","blocked_references":[],
            "primitives":[{"location":p,"tag":["rect","text","rect","text","path"][i],"source_id":None,
                "viewbox_bounds":[20+i*20,20,40+i*20,40],"visible_by_display_visibility_opacity":True} for i,p in enumerate(PARTS)]}


def annotation():
    return {"schema_version":2,"kind":"diagram-annotation","diagram_id":"test","source_url":"local:test.svg",
            "source_sha256":DIGEST,"license":"MIT","split":"unassigned",
            "review":{"status":"unreviewed","annotator_type":"unspecified","annotator":"","evidence":""},
            "objects":[{"id":"a","role":"node","name":"A","status":"unknown","parts":PARTS[:2]},
                       {"id":"b","role":"node","name":"B","status":"unknown","parts":PARTS[2:4]},
                       {"id":"arrow","role":"connector","name":"","status":"unknown","parts":PARTS[4:]}],
            "relations":[{"kind":"directed_edge","objects":["a","b"],"connector":"arrow","status":"unknown","rationale":""}],
            "coverage":{"total_primitives":5,"assigned_primitives":5,"unassigned_parts":[]}}


def test_annotation_validator_does_not_promote_unknowns_to_ground_truth():
    result=validate_annotation(annotation(),DIGEST,measurements())
    assert result["valid"] and result["objects"]==3 and result["review_status"]=="unreviewed"
    assert result["source_match_checked"] and result["primitive_inventory_checked"]
    assert annotation()["relations"][0]["status"]=="unknown"


def test_annotation_records_self_edges_even_though_current_editor_cannot_edit_them():
    data=annotation()
    data["relations"][0]["objects"]=["a","a"]
    assert validate_annotation(data,DIGEST,measurements())["valid"]


def test_review_metadata_cannot_call_an_agent_a_human():
    data=annotation()
    data["review"]={"status":"human-reviewed","annotator_type":"agent","annotator":"test-agent","evidence":"Scripted example"}
    with pytest.raises(DiagramError,match="consistent annotator"):
        validate_annotation(data)


@pytest.mark.parametrize("change",[
    lambda x:x["objects"][1]["parts"].append(PARTS[0]),
    lambda x:x["objects"][0].update(role="invented"),
    lambda x:x["objects"][0].update(id="b"),
    lambda x:x["relations"][0].update(objects=["a","absent"]),
    lambda x:x["relations"][0].update(connector=[]),
    lambda x:x["relations"][0].update(status="certain"),
    lambda x:x["coverage"].update(assigned_primitives=4),
    lambda x:x["coverage"].update(total_primitives=True),
    lambda x:x.update(split="random test data"),
])
def test_invalid_annotation_structure_rejected(change):
    data=annotation()
    change(data)
    with pytest.raises(DiagramError):
        validate_annotation(data,DIGEST,measurements())


def test_measurement_inventory_and_source_binding_are_checked():
    data=annotation()
    with pytest.raises(DiagramError,match="different SVG"):
        validate_annotation(data,"0"*64,measurements())
    data["objects"][0]["parts"][0]="svg/rect[999]"
    with pytest.raises(DiagramError,match="Unknown primitive"):
        validate_annotation(data,DIGEST,measurements())


def test_partial_coverage_remains_explicit():
    data=annotation()
    data["objects"]=data["objects"][:1]
    data["relations"]=[]
    data["coverage"]={"total_primitives":5,"assigned_primitives":2,"unassigned_parts":PARTS[2:]}
    result=validate_annotation(data,DIGEST,measurements())
    assert result["assigned_primitives"]==2 and result["total_primitives"]==5


def test_annotation_view_keeps_original_svg_in_an_image_context():
    raw=SOURCE.replace("</svg>",'<script>window.BAD=true</script></svg>')
    m=measurements();m["source_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
    page=annotation_page(raw,m,"test","local:test.svg","MIT")
    assert 'href="data:image/svg+xml;base64,' in page
    assert "<script>window.BAD" not in page
    assert 'No role or relation is prefilled' in page
    assert '__DATA_JSON__' not in page and '__IMAGE_URL__' not in page


@pytest.mark.parametrize("fragment",['<animate attributeName="x"/>','<style>@media print {rect{fill:red}}</style>',
                                      '<style>rect:hover{fill:red}</style>','<style>rect{animation:move 1s infinite}</style>'])
def test_dynamic_previews_are_rejected_instead_of_misaligned(fragment):
    raw=SOURCE.replace("</svg>",fragment+"</svg>")
    m=measurements();m["source_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
    with pytest.raises(DiagramError):
        annotation_page(raw,m,"test","local:test.svg","MIT")


def test_cli_builds_view_and_checks_downloaded_manifest(tmp_path,monkeypatch):
    source=tmp_path/"input.svg";source.write_text(SOURCE)
    measured=tmp_path/"geometry.json";measured.write_text(json.dumps(measurements()))
    out=tmp_path/"annotate.html"
    monkeypatch.setattr("sys.argv",["constraint-recovery","annotate",str(source),"--measurements",str(measured),"--output",str(out),"--license","MIT"])
    assert main()==0 and out.exists()
    record=tmp_path/"annotation.json";record.write_text(json.dumps(annotation()))
    monkeypatch.setattr("sys.argv",["constraint-recovery","check-annotation",str(record),"--source",str(source),"--measurements",str(measured)])
    assert main()==0
    source.write_text(SOURCE+"\n")
    assert main()==2


def test_published_schema_and_scripted_fixture_stay_consistent():
    root=Path(__file__).parents[1]
    schema=json.loads((root/"data/annotation-v2.schema.json").read_text())
    record=json.loads((root/"examples/styled-pipeline.annotation.agent.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(record)
    digest=hashlib.sha256((root/"examples/styled-pipeline.svg").read_bytes()).hexdigest()
    checked=validate_annotation(record,digest)
    assert checked["valid"] and checked["review_status"]=="agent-reviewed"
