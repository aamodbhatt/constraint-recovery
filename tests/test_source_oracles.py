"""External authoring references must not become self-generated gold labels."""
import base64
from urllib.parse import quote
import xml.etree.ElementTree as ET
import zlib
import pytest
from defusedxml.common import DefusedXmlException
from benchmarks import audit_source_oracles as audit


def svg(model,compressed=False,encoded=False):
    page=ET.Element('diagram',name='test')
    if compressed:
        compressor=zlib.compressobj(wbits=-15)
        raw=compressor.compress(quote(model,safe='').encode())+compressor.flush()
        page.text=base64.b64encode(raw).decode()
    else:page.append(ET.fromstring(model))
    document=ET.Element('mxfile');document.append(page)
    content=ET.tostring(document,encoding='unicode')
    if encoded:content=quote(content,safe='')
    root=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',content=content)
    return ET.tostring(root,encoding='unicode')


MODEL='''<mxGraphModel><root><mxCell id="0"/>
<object id="a"><mxCell vertex="1" parent="0"/></object>
<mxCell id="b" vertex="1" parent="0"/>
<mxCell id="e" edge="1" source="a" target="b" style="endArrow=none;"/>
<mxCell id="free" edge="1" source="a"/>
</root></mxGraphModel>'''


@pytest.mark.parametrize('compressed,encoded',[(False,False),(True,False),(True,True)])
def test_compressed_and_legacy_percent_payloads_preserve_only_declared_bindings(compressed,encoded):
    page=audit.graph_reference(svg(MODEL,compressed,encoded))['pages'][0]
    assert (page['vertices'],page['edges'],page['bound_edges'])==(2,2,1)
    assert page['bindings'][0]['end_arrow']=='none'
    assert page['bindings'][1]['target'] is None
    assert 'directed' not in page['bindings'][0]


def test_no_graph_payload_is_not_inferred_from_visible_artwork():
    with pytest.raises(ValueError,match='No embedded'):
        audit.graph_reference('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L20 0"/></svg>')


def test_duplicate_cell_ids_refused():
    with pytest.raises(ValueError,match='duplicate'):
        audit.graph_reference(svg(MODEL.replace('id="b"','id="a"')))


def test_compressed_trailing_data_refused():
    source=ET.fromstring(svg(MODEL,compressed=True))
    document=ET.fromstring(source.get('content'));page=document.find('diagram')
    page.text=base64.b64encode(base64.b64decode(page.text)+b'junk').decode()
    source.set('content',ET.tostring(document,encoding='unicode'))
    with pytest.raises(ValueError,match='trailing compressed'):
        audit.graph_reference(ET.tostring(source,encoding='unicode'))


def test_compression_expansion_budget_refuses_incomplete_references(monkeypatch):
    source=svg('<mxGraphModel><root>'+(' '*4000)+'</root></mxGraphModel>',compressed=True)
    monkeypatch.setattr(audit,'LIMIT',800)
    assert len(source.encode())<800
    with pytest.raises(ValueError,match='Oversized'):
        audit.graph_reference(source)


def test_nonrendering_parser_does_not_expand_entities():
    with pytest.raises(DefusedXmlException):
        audit.parse_xml('<!DOCTYPE svg [<!ENTITY x "unsafe">]><svg>&x;</svg>')
