from copy import deepcopy
import json
from pathlib import Path
import pytest
from constraint_recovery.model import Diagram, DiagramError
from constraint_recovery.svg import parse_svg, render_svg
from constraint_recovery.layout import edit
from constraint_recovery.check import verify
from constraint_recovery.cli import main

SOURCE = Path(__file__).parents[1]/"examples/pipeline.svg"


def source():
    return parse_svg(SOURCE.read_text())


def test_recovery_and_graph_roundtrip():
    d = source()
    assert [(e.source,e.target) for e in d.edges]==[("data","model"),("model","result")]
    assert Diagram.from_dict(d.to_dict()).to_dict()==d.to_dict()


@pytest.mark.parametrize("options",[
    {"labels":{"model":"Much longer model description that requires multiple text lines"}},
    {"font_size":24},
    {"width":300,"height":620,"flow":"vertical","font_size":20},
])
def test_supported_edits_are_checked_after_serialization(options):
    d = source()
    result, _ = edit(d,**options)
    actual = parse_svg(render_svg(result),tolerance=.01)
    check = verify(d,actual,options.get("labels"),options.get("font_size",0))
    assert check["passed"],check
    assert d.to_dict()==source().to_dict(),"Editing must not mutate the original"


def test_impossible_canvas_fails():
    with pytest.raises(DiagramError,match="Infeasible"):
        edit(source(),width=80,height=60,font_size=30)


def test_unknown_label_target_fails():
    with pytest.raises(DiagramError,match="Unknown"):
        edit(source(),labels={"typo":"new text"})


@pytest.mark.parametrize("fragment",[
    '<script>alert(1)</script>',
    '<image href="https://example.com/file.svg"/>',
    '<g transform="translate(1,2)"/>',
    '<rect x="1" y="2" width="10" height="10" onclick="alert(1)"/>',
])
def test_unsupported_or_active_content_is_rejected(fragment):
    text = SOURCE.read_text().replace("</svg>",fragment+"</svg>")
    with pytest.raises(DiagramError):
        parse_svg(text)


def test_ambiguous_arrow_does_not_guess():
    text = '<svg width="400" height="200"><rect id="a" x="20" y="20" width="100" height="60"/><rect id="b" x="120" y="20" width="100" height="60"/><line x1="120" y1="50" x2="220" y2="50" marker-end="url(#arrow)"/></svg>'
    with pytest.raises(DiagramError,match="Ambiguous"):
        parse_svg(text)


def test_checker_detects_tampered_label_connector_and_overlap():
    d = source()
    actual = deepcopy(d)
    actual.nodes[0].label = "tampered"
    actual.nodes[1].x = actual.nodes[0].x
    actual.edges[0].points[0] = [0,0]
    actual.edges[0].target = "result"
    errors = verify(d,actual)["errors"]
    assert any("label" in e for e in errors)
    assert any("overlap" in e for e in errors)
    assert any("Detached" in e for e in errors)
    assert "Directed connector graph changed" in errors


def test_conflicting_flow_cycle_fails_without_false_success():
    d = source()
    d.edges[1].target = "data"
    with pytest.raises(DiagramError,match="No feasible"):
        edit(d,flow="vertical")


def test_checker_independently_rejects_wrong_flow():
    d = source()
    assert any("flow" in e for e in verify(d,d,flow="vertical",gap=24)["errors"])


def test_cli_reports_verified_artifact(tmp_path,monkeypatch):
    out = tmp_path/"edited.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--output",str(out),"--width","300","--height","620","--flow","vertical"])
    assert main()==0
    assert json.loads(out.with_suffix(".report.json").read_text())["verification"]["passed"]
    assert out.with_suffix(".html").exists()
    assert out.with_suffix(".original.svg").read_text()==SOURCE.read_text()


def test_cli_failure_does_not_export(tmp_path,monkeypatch):
    out = tmp_path/"edited.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--output",str(out),"--width","40"])
    assert main()==2
    assert not out.exists()
