import json
from pathlib import Path
import numpy as np
import pytest
from constraint_recovery.geometry import transform,point
from constraint_recovery.inventory import inspect_svg
from constraint_recovery.model import DiagramError
from constraint_recovery.cli import main


def test_affine_inventory_does_not_relax_editor_transform_support():
    assert point(transform("rotate(90 10 20)",allow_affine=True),20,20)==pytest.approx([10,30])
    assert point(transform("skewX(45)",allow_affine=True),1,2)==pytest.approx([3,2])
    with pytest.raises(DiagramError):
        transform("rotate(90 10 20)")


def test_inventory_distinguishes_background_definitions_and_ambiguous_owners():
    raw='''<svg width="400" height="300"><defs><rect width="5" height="5"/></defs>
    <rect width="400" height="300"/><rect x="20" y="20" width="200" height="200"/>
    <rect x="40" y="40" width="100" height="60"/><text x="80" y="70">Inside</text>
    <text x="350" y="250">Outside</text><circle cx="300" cy="80" r="20"/></svg>'''
    result = inspect_svg(raw)
    s = result["summary"]
    assert s["canvas_covering_rectangles"]==1 and s["other_rectangles"]==2
    assert s["text_anchors_with_multiple_rect_owners"]==1
    assert s["text_anchors_with_zero_rect_owners"]==1
    assert s["visible_tags"]["rect"]==3 and result["all_element_counts"]["rect"]==4
    assert result["primitives"][-1]["bounds"]==[280,60,320,100]
    assert "Inside" not in json.dumps(result)


def test_inventory_affine_ellipse_envelope():
    raw='<svg viewBox="10 20 200 200"><g transform="translate(10 20) rotate(90)"><ellipse cx="30" cy="40" rx="20" ry="10"/></g></svg>'
    box=inspect_svg(raw)["primitives"][0]["bounds"]
    assert box==pytest.approx([-50,10,-30,50])


def test_bad_ancestor_geometry_is_not_reported_as_reliable_bounds():
    result=inspect_svg('<svg width="200" height="200"><g transform="nonsense(3)"><rect width="40" height="30"/></g></svg>')
    assert result["primitives"][0]["bounds"] is None
    assert result["primitives"][0]["geometry_failure"]


def test_inventory_records_external_and_active_signals_without_fetching(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("Inventory must never fetch")
    monkeypatch.setattr("urllib.request.urlopen",forbidden)
    raw='<svg width="200" height="200"><script>bad()</script><image width="50" height="50" href="https://example.com/a.png" onclick="bad()"/></svg>'
    result=inspect_svg(raw)
    assert result["reference_counts"]=={"external":1}
    assert result["active_content_signals"]=={"script":1,"event_attributes":1}


def test_inventory_budget_rejects_partial_coverage():
    with pytest.raises(DiagramError,match="budget"):
        inspect_svg('<svg width="200" height="200"><rect width="40" height="30"/><rect width="40" height="30"/></svg>',max_primitives=1)


def test_cli_inspect_does_not_claim_edit_support(tmp_path,monkeypatch):
    source=Path(__file__).parents[1]/"examples/styled-pipeline.svg"
    out=tmp_path/"inventory.json"
    monkeypatch.setattr("sys.argv",["constraint-recovery","inspect",str(source),"--output",str(out)])
    assert main()==0
    data=json.loads(out.read_text())
    assert data["summary"]["visible_primitives"]==5
    assert "not an editable graph" in data["limitations"][0]
