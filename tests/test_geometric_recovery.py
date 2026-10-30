from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from constraint_recovery.geometric_recovery import recover,validate_observations
from benchmarks.source_recovery import blind_source,poison_source,score_predictions,normalize,make_observations,ground_reference,parse_xml,XML


def observations():
    nodes=[dict(id='p-'+str(i)*12,tag='rect',bounds=b,closed=True,filled=True,stroked=True,path=None)
        for i,b in [(1,[0,0,40,30]),(2,[100,0,140,30])]]
    edge=dict(id='p-'+'3'*12,tag='line',bounds=[40,15,99,15],closed=False,filled=False,stroked=True,
        path=dict(start=[40,15],end=[99,15],start_direction=[1,0],end_direction=[1,0]))
    return dict(schema_version=1,kind='blind-primitive-geometry',canvas=[150,50],primitives=nodes+[edge])


def test_geometry_recovery_permutation_and_direction():
    data=observations();result=recover(data);data['primitives'].reverse()
    assert recover(data)==result
    for edges in result['methods'].values():
        assert edges[0]['source']['node']=='p-'+'1'*12
        assert edges[0]['target']['node']=='p-'+'2'*12


@pytest.mark.parametrize('field',['source','reference','source_sha256','text'])
def test_geometry_contract_rejects_semantic_input(field):
    data=observations();data[field]='hidden-answer'
    with pytest.raises(ValueError,match='source or oracle'):validate_observations(data)


def test_symmetric_candidates_abstain_instead_of_using_list_order():
    data=observations();data['primitives'][1]['bounds']=data['primitives'][0]['bounds'][:]
    assert all(e[0]['source']['node'] is None for e in recover(data)['methods'].values())


def test_hidden_graph_mutation_preserves_blinded_artwork():
    source=(Path(__file__).parents[1]/'examples/source-reference.svg').read_text()
    assert poison_source(source)!=source
    assert blind_source(source)['blinded']==blind_source(poison_source(source))['blinded']


def test_unrewritten_stylesheet_and_unknown_dtd_refused():
    with pytest.raises(ValueError,match='stylesheet'):
        blind_source('<svg xmlns="http://www.w3.org/2000/svg"><style>#answer{fill:red}</style></svg>')
    with pytest.raises(ValueError,match='known legacy'):
        normalize('<!DOCTYPE svg SYSTEM "file:///private-data"><svg/>')


def test_scorer_binding_and_abstention_denominators():
    data=observations();raw=json.dumps(data).encode();digest=hashlib.sha256(raw).hexdigest()
    prediction=recover(data);prediction['observation_sha256']=digest
    reference=dict(observation_sha256=digest,declared_vertices=2,declared_edges=1,nodes=prediction['node_candidates'],
        edges=[dict(shaft='p-'+'3'*12,source='p-'+'1'*12,target='p-'+'2'*12)])
    assert score_predictions(prediction,reference,raw)['methods']['nearest_boundary']['correct_endpoints']==2
    changed=deepcopy(prediction);changed['methods']['nearest_boundary'][0]['target']['node']=None
    metric=score_predictions(changed,reference,raw)['methods']['nearest_boundary']
    assert metric['reference_endpoints']==2 and metric['endpoint_accuracy']==.5 and metric['both_end_accuracy']==0
    reference['observation_sha256']='0'*64
    with pytest.raises(ValueError,match='Reference/input'):score_predictions(prediction,reference,raw)


def fixture_measurements(blinded):
    records=[]
    for index,tag,bounds,path in [(0,'rect',[20,20,90,60],None),(2,'path',[90,40,199,40],dict(start=[90,40],end=[199,40],start_direction=[1,0],end_direction=[1,0])),
        (3,'path',[199,35.5,208,44.5],dict(start=[208,40],end=[208,40],start_direction=[-9,-4.5],end_direction=[9,-4.5])),(4,'rect',[210,20,280,60],None)]:
        record=dict(location=f'svg/g[0]/{tag}[{index}]',tag=tag,viewbox_bounds=bounds,visible_by_display_visibility_opacity=True,
            computed=dict(fill='white' if tag=='rect' else 'none',stroke='#222',stroke_width='1px'))
        if path:record['path_geometry']=path
        records.append(record)
    return dict(source_sha256=hashlib.sha256(blinded.encode()).hexdigest(),canvas=[300,140],primitives=records)


def test_reference_grounding_checks_source_positions_without_predictions():
    source=(Path(__file__).parents[1]/'examples/source-reference.svg').read_text();blinded=blind_source(source)['blinded']
    measured=fixture_measurements(blinded);data,locations=make_observations(blinded,measured)
    reference=ground_reference(source,blinded,measured,locations)
    assert len(reference['nodes'])==2 and len(reference['edges'])==1
    root=parse_xml(source);model=parse_xml(root.get('content'))
    next(c for c in model.iter('mxCell') if c.get('id')=='b').find('mxGeometry').set('x','220')
    root.set('content',XML.tostring(model,encoding='unicode'))
    changed=XML.tostring(root,encoding='unicode')
    assert blind_source(changed)['blinded']==blinded
    with pytest.raises(ValueError,match='one translation'):
        ground_reference(changed,blinded,measured,locations)


def test_head_at_wrong_end_and_missing_visible_parts_refuse_grounding():
    source=(Path(__file__).parents[1]/'examples/source-reference.svg').read_text();blinded=blind_source(source)['blinded']
    measured=fixture_measurements(blinded);_,locations=make_observations(blinded,measured)
    measured['primitives'][2]['viewbox_bounds']=[80,35.5,90,44.5]
    with pytest.raises(ValueError,match='terminal end'):
        ground_reference(source,blinded,measured,locations)
    del locations['svg/g[0]/path[2]']
    with pytest.raises(ValueError,match='invisible or unmeasured'):
        ground_reference(source,blinded,measured,locations)


def test_functional_fragment_ids_survive_anonymization():
    source='<svg xmlns="http://www.w3.org/2000/svg" data-answer="secret"><defs><marker id="source-node"/></defs><path id="source-edge" marker-end="url(#source-node)"/></svg>'
    blinded=blind_source(source)['blinded']
    assert 'source-node' not in blinded and 'source-edge' not in blinded and 'secret' not in blinded
    root=parse_xml(blinded);marker=next(e for e in root.iter() if e.tag.endswith('marker'))
    path=next(e for e in root.iter() if e.tag.endswith('path'))
    assert path.get('marker-end')=='url(#'+marker.get('id')+')'
