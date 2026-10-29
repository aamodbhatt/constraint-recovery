import hashlib
import json
from pathlib import Path
import pytest
from constraint_recovery.model import Diagram,DiagramError
from constraint_recovery.svg import parse_svg
from constraint_recovery.cli import main

ROOT=Path(__file__).parents[1]
SOURCE=ROOT/"examples/pipeline.svg"


def test_recovered_graph_digest_survives_json_roundtrip():
    raw=SOURCE.read_text()
    d=parse_svg(raw)
    assert d.source_sha256==hashlib.sha256(raw.encode()).hexdigest()
    assert Diagram.from_dict(d.to_dict()).source_sha256==d.source_sha256


@pytest.mark.parametrize("digest",["wrong","a"*63,"G"*64,12])
def test_invalid_digest_rejected(digest):
    d=parse_svg(SOURCE.read_text()).to_dict()
    d["source_sha256"]=digest
    with pytest.raises(DiagramError,match="digest"):
        Diagram.from_dict(d)


def test_cli_output_sidecar_binds_next_edit_and_rejects_stale_source(tmp_path,monkeypatch):
    first=tmp_path/"first.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--output",str(first),"--font-size","20"])
    assert main()==0
    sidecar=first.with_suffix(".constraints.json")
    digest=json.loads(sidecar.read_text())["source_sha256"]
    assert digest==hashlib.sha256(first.read_bytes()).hexdigest()
    report=json.loads(first.with_suffix(".report.json").read_text())
    assert report["output_sha256"]==digest
    second=tmp_path/"second.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(first),"--constraints",str(sidecar),"--output",str(second),"--height","500"])
    assert main()==0
    modified=tmp_path/"changed.svg"
    modified.write_text(first.read_text()+"\n")
    invalid=tmp_path/"invalid.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(modified),"--constraints",str(sidecar),"--output",str(invalid)])
    assert main()==2 and not invalid.exists()


def test_bound_reviewed_graph_resolves_ambiguous_input_before_automatic_recovery(tmp_path,monkeypatch):
    source=ROOT/"examples/ambiguous.svg"
    d=parse_svg(source.read_text(),attachment_overrides={"ambiguous-result":{"source":"option-a","target":"result"}})
    reviewed=tmp_path/"reviewed.json"
    reviewed.write_text(json.dumps(d.to_dict()))
    out=tmp_path/"edited.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(source),"--constraints",str(reviewed),"--output",str(out)])
    assert main()==0
    assert [(e.source,e.target) for e in parse_svg(out.read_text()).edges]==[("option-a","result")]


def test_legacy_unbound_graph_is_explicitly_marked(tmp_path,monkeypatch):
    graph=parse_svg(SOURCE.read_text()).to_dict()
    graph.pop("source_sha256")
    reviewed=tmp_path/"legacy.json"
    reviewed.write_text(json.dumps(graph))
    out=tmp_path/"edited.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--constraints",str(reviewed),"--output",str(out)])
    assert main()==0
    assert any("Legacy constraint graph" in s for s in json.loads(out.with_suffix(".report.json").read_text())["warnings"])
