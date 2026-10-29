from copy import deepcopy
import json
from pathlib import Path
import pytest
from constraint_recovery.compound import accepted_annotation,affine,portals,next_state,json_digest
from constraint_recovery.model import DiagramError,Node
from constraint_recovery.routing import OrthogonalRouter
from constraint_recovery.static_svg import parse_static,elements

ROOT=Path(__file__).parents[1]


@pytest.mark.parametrize("fragment",[
    '<script>alert(1)</script>','<foreignObject/>','<image href="https://example.com/a.png"/>',
    '<g onclick="bad()"/>','<g xml:base="https://example.com/"/>',
    '<style>rect{transform:translate(2px,3px)}</style>','<style>rect{animation:x 1s}</style>',
    '<style>@import "https://example.com/a.css";</style>',
    r'<style>rect{fill:u\72l("https://example.com/a.svg")}</style>',
    '<style>rect:hover{fill:red}</style>','<svg width="10" height="10"/>',
])
def test_static_edit_guard_rejects_active_external_or_unmodeled_sources(fragment):
    with pytest.raises(DiagramError):
        parse_static('<svg xmlns="http://www.w3.org/2000/svg">'+fragment+'</svg>')


def test_static_parser_preserves_comments_and_element_locations():
    r=parse_static('<svg xmlns="http://www.w3.org/2000/svg"><!-- license --><g transform="rotate(20)"><circle id="a" r="5"/></g></svg>')
    assert elements(r)['svg/g[0]/circle[0]'].get('id')=='a'
    assert list(r)[0].text==' license '


def test_custom_anchor_routing_does_not_snap_to_box_centers():
    nodes={'a':Node('a',20,20,100,100),'b':Node('b',300,150,100,100)}
    start=portals([20,20,120,120],[120,45],[1,0])
    end=portals([300,150,400,250],[300,210],[-1,0])
    router=OrthogonalRouter(nodes,500,350,extra_points=[p[1] for p in start+end])
    points,_=router.route('a','b',start,end)
    assert points[0]==[120,45] and points[-1]==[300,210]


def test_far_or_directionless_anchors_are_rejected():
    with pytest.raises(DiagramError):
        portals([20,20,120,120],[200,200],[1,0])
    with pytest.raises(DiagramError):
        portals([20,20,120,120],[120,60],[0,0])


def test_constraint_state_retains_original_annotation_review():
    annotation=json.loads((ROOT/'examples/compound.annotation.agent.json').read_text())
    report={'input_sha256':annotation['source_sha256'],'output_sha256':'a'*64}
    state=next_state(annotation,report,{'decoder':[1,2]})
    assert state['annotation']==annotation and state['annotation']['source_sha256']!=state['source_sha256']
    assert state['annotation_sha256']==json_digest(annotation)
    assert state['annotation']['review']['status']=='agent-reviewed'
    second=next_state(state,{'input_sha256':'a'*64,'output_sha256':'b'*64},{'decoder':[2,3]})
    assert len(second['history'])==2 and second['annotation']==annotation


def test_broken_or_stale_derived_state_is_rejected():
    annotation=json.loads((ROOT/'examples/compound.annotation.agent.json').read_text())
    state=next_state(annotation,{'input_sha256':annotation['source_sha256'],'output_sha256':'a'*64},{'decoder':[1,2]})
    with pytest.raises(DiagramError,match='different source'):
        accepted_annotation(state,'b'*64,{})
    state['history'][0]['input_sha256']='c'*64
    with pytest.raises(DiagramError,match='provenance'):
        accepted_annotation(state,'a'*64,{})
