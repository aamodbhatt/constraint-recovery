"""Frozen development-source integrity and conservative annotation boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from jsonschema import Draft202012Validator
from constraint_recovery.annotation import validate_annotation
from constraint_recovery.model import DiagramError
from constraint_recovery.static_svg import parse_static,elements

ROOT=Path(__file__).parents[1]
NS='http://www.w3.org/2000/svg'
RDF='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
SODIPODI='http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'


def test_frozen_native_sources_and_agent_annotations_match_the_declared_manifest():
    selection=json.loads((ROOT/'data/native-pilot-selection.json').read_text())
    schema=Draft202012Validator(json.loads((ROOT/'data/annotation-v2.schema.json').read_text()))
    assert len(selection['cases'])==5 and selection['article_clusters']==2
    for entry in selection['cases']:
        raw=(ROOT/'data/native-pilot/original'/f'{entry["id"]}.svg').read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['source_sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['git_blob']
        annotation=json.loads((ROOT/'data/native-pilot/annotations'/f'{entry["id"]}.agent.json').read_text())
        schema.validate(annotation)
        assert validate_annotation(annotation,entry['source_sha256'])['review_status']=='agent-reviewed'
        assert annotation['split']=='development'


def test_known_editor_and_rdf_metadata_are_preserved_without_becoming_renderable_svg():
    source=f'<svg xmlns="{NS}" xmlns:s="{SODIPODI}" xmlns:r="{RDF}"><s:namedview id="editor"/><metadata><r:RDF><r:Description r:about="source"/></r:RDF></metadata><rect id="art" width="20" height="20"/></svg>'
    root=parse_static(source)
    serialized=ET.tostring(root,encoding='unicode')
    reloaded=parse_static(serialized)
    assert list(reloaded)[0].tag==f'{{{SODIPODI}}}namedview'
    assert elements(reloaded)['svg/metadata[1]/RDF[0]/Description[0]'].get(f'{{{RDF}}}about')=='source'
    assert elements(reloaded)['svg/rect[2]'].get('id')=='art'


@pytest.mark.parametrize('content',[
    f'<r:RDF xmlns:r="{RDF}"/>',
    f'<g><s:namedview xmlns:s="{SODIPODI}"/></g>',
    f'<s:namedview xmlns:s="{SODIPODI}"><rect width="1" height="1"/></s:namedview>',
    f'<metadata><r:RDF xmlns:r="{RDF}" onload="bad()"/></metadata>',
    f'<metadata><r:RDF xmlns:r="{RDF}"><foreignObject/></r:RDF></metadata>',
])
def test_inert_metadata_allowance_does_not_admit_active_or_misplaced_foreign_content(content):
    with pytest.raises(DiagramError):
        parse_static(f'<svg xmlns="{NS}">{content}</svg>')


@pytest.mark.parametrize('change',[
    lambda o:o['connector_geometry'].update(direction='reverse'),
    lambda o:o['connector_geometry'].update(shaft='absent'),
    lambda o:o['connector_geometry']['end_head'].update(part=o['connector_geometry']['shaft']),
    lambda o:o['connector_geometry']['end_head'].update(tip=[float('inf'),0]),
    lambda o:o['connector_geometry']['end_head'].update(tip=[True,0]),
    lambda o:o['connector_geometry'].update(extra='unrecognized'),
    lambda o:o.update(role='node'),
    lambda o:o['parts'].append('unaccounted-part'),
])
def test_separate_arrowhead_geometry_must_be_explicit_finite_and_cover_its_parts(change):
    annotation=json.loads((ROOT/'data/native-pilot/annotations/distill-rnn-basic.agent.json').read_text())
    obj=next(o for o in annotation['objects'] if o.get('connector_geometry'))
    change(obj)
    with pytest.raises(DiagramError):
        validate_annotation(annotation)
