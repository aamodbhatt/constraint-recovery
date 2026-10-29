import hashlib
import json
from pathlib import Path
import pytest
from constraint_recovery.model import DiagramError
from constraint_recovery.svg import parse_svg
from constraint_recovery.source import SourceDocument
from constraint_recovery.recovery import load_overrides
from constraint_recovery.review import render_review
from constraint_recovery.cli import main

ROOT=Path(__file__).parents[1]
SOURCE=ROOT/"examples/ambiguous.svg"


def choices(source=None):
    return {"schema_version":1,"kind":"attachment-overrides","source_sha256":hashlib.sha256((source or SOURCE.read_text()).encode()).hexdigest(),
            "decisions":{"ambiguous-result":{"source":"option-a","target":"result"}}}


def test_review_collects_ambiguity_without_promoting_partial_graph():
    raw=SOURCE.read_text()
    with pytest.raises(DiagramError,match="Ambiguous"):
        parse_svg(raw)
    r=parse_svg(raw,review=True)
    assert r["kind"]=="attachment-review" and not r["automatic_recovery_complete"]
    assert r["unresolved_endpoints"]==1
    assert r["connectors"][0]["source"]["selected"] is None
    assert [v["node_id"] for v in r["connectors"][0]["source"]["candidates"][:2]]==["option-a","option-b"]
    assert r["connectors"][0]["target"]["selected"]=="result"


def test_source_bound_choices_enable_recovery_and_mark_evidence():
    raw=SOURCE.read_text()
    overrides=load_overrides(choices(),raw)
    d=parse_svg(raw,attachment_overrides=overrides)
    assert [(e.source,e.target) for e in d.edges]==[("option-a","result")]
    assert "user-supplied" in d.edges[0].evidence
    with pytest.raises(DiagramError,match="different source"):
        load_overrides(choices(),raw+"\n")


@pytest.mark.parametrize("decisions",[{"absent":{"source":"option-a"}}, {"ambiguous-result":{"source":"absent"}},
                                      {"ambiguous-result":{"unknown":"option-a"}},[],{"ambiguous-result":{"source":[]}}])
def test_invalid_override_ids_and_schema_cannot_change_graph(decisions):
    with pytest.raises(DiagramError):
        parse_svg(SOURCE.read_text(),attachment_overrides=decisions)


def test_source_preserving_review_requires_acceptance_before_export():
    raw=(ROOT/"examples/styled-pipeline.svg").read_text()
    doc=SourceDocument(raw,review=True)
    assert doc.review["automatic_recovery_complete"] and doc.diagram is None
    with pytest.raises(DiagramError,match="not an accepted graph"):
        doc.export(None)


def test_review_preview_escapes_script_content_and_normalizes_paint():
    r=parse_svg(SOURCE.read_text(),review=True)
    r["nodes"][0]["label"]='</script><script>window.BAD=true</script>'
    r["nodes"][0]["lines"]=[r["nodes"][0]["label"]]
    r["nodes"][0]["fill"]='url(https://example.com/bad.svg)'
    page=render_review(r)
    assert "<script>window.BAD" not in page
    assert "url(https://example.com" not in page.partition('<script type=')[0]
    assert "&lt;/script&gt;" in page
    assert "\\u003c/script>" in page


def test_cli_review_and_explicit_choices_produce_verified_edit(tmp_path,monkeypatch):
    out=tmp_path/"review.json"
    monkeypatch.setattr("sys.argv",["constraint-recovery","review",str(SOURCE),"--output",str(out)])
    assert main()==0
    assert json.loads(out.read_text())["unresolved_endpoints"]==1 and out.with_suffix(".html").exists()
    override=tmp_path/"choices.json"
    override.write_text(json.dumps(choices()))
    edited=tmp_path/"accepted.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--attachments",str(override),"--output",str(edited)])
    assert main()==0
    report=json.loads(edited.with_suffix(".report.json").read_text())
    assert report["verification"]["passed"] and report["attachment_overrides"]==choices()["decisions"]


def test_cli_rejects_changed_source_manifest_without_export(tmp_path,monkeypatch):
    override=tmp_path/"choices.json"
    manifest=choices()
    manifest["source_sha256"]="wrong"
    override.write_text(json.dumps(manifest))
    out=tmp_path/"wrong.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--attachments",str(override),"--output",str(out)])
    assert main()==2 and not out.exists()


def test_review_svg_ids_cannot_collide_with_html_controls():
    raw=SOURCE.read_text().replace('id="option-a"','id="observations"')
    page=render_review(parse_svg(raw,review=True))
    assert page.count('id="observations"')==1
    assert 'data-node="observations"' in page


def test_review_companion_cannot_overwrite_source(tmp_path,monkeypatch):
    source=tmp_path/"same.html"
    source.write_text(SOURCE.read_text())
    monkeypatch.setattr("sys.argv",["constraint-recovery","review",str(source),"--output",str(source.with_suffix('.json'))])
    assert main()==2 and source.read_text()==SOURCE.read_text()


def test_cli_binds_and_preserves_utf8_source_bytes_with_crlf(tmp_path,monkeypatch):
    raw=SOURCE.read_bytes().replace(b"\n",b"\r\n")
    source=tmp_path/"crlf.svg"
    source.write_bytes(raw)
    observations=tmp_path/"review.json"
    monkeypatch.setattr("sys.argv",["constraint-recovery","review",str(source),"--output",str(observations)])
    assert main()==0
    digest=json.loads(observations.read_text())["source_sha256"]
    assert digest==hashlib.sha256(raw).hexdigest()
    manifest=choices()
    manifest["source_sha256"]=digest
    override=tmp_path/"choices.json"
    override.write_text(json.dumps(manifest))
    out=tmp_path/"edited.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(source),"--attachments",str(override),"--output",str(out)])
    assert main()==0 and out.with_suffix(".original.svg").read_bytes()==raw


def test_conflicting_review_inputs_fail_before_export(tmp_path,monkeypatch):
    override=tmp_path/"choices.json"
    override.write_text(json.dumps(choices()))
    graph=parse_svg(SOURCE.read_text(),attachment_overrides=choices()["decisions"]).to_dict()
    graph["edges"][0]["source"]="option-b"
    constraints=tmp_path/"graph.json"
    constraints.write_text(json.dumps(graph))
    out=tmp_path/"conflict.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--attachments",str(override),"--constraints",str(constraints),"--output",str(out)])
    assert main()==2 and not out.exists()
