from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from constraint_recovery.geometry import transform,point,curve_points
from constraint_recovery.model import DiagramError
from constraint_recovery.source import SourceDocument,styles
from constraint_recovery.layout import edit
from constraint_recovery.check import verify
from constraint_recovery.cli import main

SOURCE = Path(__file__).parents[1]/"examples/styled-pipeline.svg"


def test_svg_transform_order_and_nesting():
    matrix = transform("translate(40, 40) scale(1.2)")
    assert point(matrix,20,60)==pytest.approx([64,112])
    assert point(transform("matrix(2 0 0 2 3 4)"),5,6)==[13,16]


@pytest.mark.parametrize("raw",["scale(-1)","rotate(90)","skewX(3)","scale(1,2)","scale(0)","translate(NaN)","translate(1) bad"])
def test_unsupported_transforms_fail(raw):
    with pytest.raises(DiagramError):
        transform(raw)


def test_bounded_bezier_subdivision_captures_bulge():
    pts = curve_points("M0 0 C0 100 100 100 100 0",np.eye(3))
    assert pts[0]==[0,0] and pts[-1]==[100,0]
    assert max(p[1] for p in pts)==pytest.approx(75)
    assert len(pts)>10
    with pytest.raises(DiagramError,match="budget"):
        curve_points("M0 0 C0 100 100 100 100 0",np.eye(3),max_points=3)


@pytest.mark.parametrize("path",["M0 0 A10 10 0 0 1 20 0","M0 0 L10 0 M30 0 L40 0","M0 0L10 0Z"])
def test_unsupported_path_geometry_is_explicit(path):
    with pytest.raises(DiagramError):
        curve_points(path,np.eye(3))


def test_source_recovery_and_exact_noop():
    raw = SOURCE.read_text()
    doc = SourceDocument(raw)
    assert doc.diagram.nodes[0].x==pytest.approx(54)
    assert doc.diagram.nodes[0].y==pytest.approx(92)
    assert doc.diagram.nodes[0].font_size==pytest.approx(19.2)
    assert [(e.source,e.target) for e in doc.diagram.edges]==[("data","model")]
    assert len(doc.diagram.edges[0].points)>2
    assert doc.export(deepcopy(doc.diagram))==raw


def test_source_export_preserves_defs_styles_metadata_and_hierarchy():
    doc = SourceDocument(SOURCE.read_text())
    result,_ = edit(doc.diagram,labels={"model":"Recovered structure"},width=330,height=650,flow="vertical")
    exported = doc.export(result)
    parsed = SourceDocument(exported,tolerance=.01)
    checks = verify(doc.diagram,parsed.diagram,{"model":"Recovered structure"},flow="vertical",gap=24)
    assert checks["passed"],checks
    ns = {"s":"http://www.w3.org/2000/svg"}
    before,after = doc.root,ET.fromstring(exported)
    for tag in ["defs","style","title","metadata"]:
        assert ET.tostring(before.find("s:"+tag,ns))==ET.tostring(after.find("s:"+tag,ns))
    assert after.find(".//s:g[@data-role='model']/s:rect",ns).get("id")=="model"
    assert after.find(".//s:path[@id='data-model']",ns).get("class")=="connector"
    assert after.find(".//s:text[@id='model-label']",ns) is not None
    assert SourceDocument(SOURCE.read_text()).diagram.to_dict()==doc.diagram.to_dict()


def test_css_cascade_important_specificity_and_inheritance():
    root = ET.fromstring('''<svg><style>rect{fill:red !important}.node{fill:blue} #a{stroke:green}</style>
      <g font-size="18"><rect id="a" class="node" style="fill:orange;stroke:black !important"/></g></svg>''')
    values = styles(root)[root.find(".//rect")]
    assert values["fill"]=="red" and values["stroke"]=="black" and values["font-size"]=="18"


@pytest.mark.parametrize("fragment",[
    '<image href="https://example.com/a.png"/>',
    '<script>alert(1)</script>',
    '<g transform="rotate(20)"/>',
    '<g style="transform:translate(10px,20px)"/>',
    '<style>@import "https://example.com/a.css";</style>',
    '<style>.node{fill:url(https://example.com/a.svg)}</style>',
    r'<style>.node{fill:u\72l("https://example.com/a.svg")}</style>',
    '<style>.node{width:400px}</style>',
    '<style>rect:hover{fill:red}</style>',
    '<g onclick="alert(1)"/>',
    '<g clip-path="url(#clip)"/>',
    '<style media="print">rect{fill:red}</style>',
    '<g transform-origin="center"/>',
])
def test_extended_import_still_rejects_unsafe_or_unmodeled_content(fragment):
    with pytest.raises(DiagramError):
        SourceDocument(SOURCE.read_text().replace("</svg>",fragment+"</svg>"))


def test_source_export_rejects_style_change_triggered_by_geometry_selector():
    raw = SOURCE.read_text().replace("</style>",'rect[x="20"] {fill:red}</style>')
    doc = SourceDocument(raw)
    result,_ = edit(doc.diagram,width=330,height=650,flow="vertical")
    with pytest.raises(DiagramError,match="computed source paint"):
        doc.export(result)


def test_cli_source_preserving_roundtrip(tmp_path,monkeypatch):
    out = tmp_path/"styled.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(SOURCE),"--source-preserving",
                                   "--output",str(out),"--width","330","--height","650","--flow","vertical"])
    assert main()==0
    report = json.loads(out.with_suffix(".report.json").read_text())
    assert report["export_mode"]=="source-preserving" and report["verification"]["passed"]


@pytest.mark.parametrize("header",['<?xml-stylesheet href="https://example.com/a.xsl" type="text/xsl"?>','<!DOCTYPE svg SYSTEM "https://example.com/svg.dtd">'])
def test_discarded_xml_instructions_cannot_survive_original_embed(header):
    from constraint_recovery.svg import parse_svg
    for parse in [parse_svg,SourceDocument]:
        with pytest.raises(DiagramError,match="processing instructions"):
            parse(header+SOURCE.read_text())
