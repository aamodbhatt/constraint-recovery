from copy import deepcopy
import json
import math
from pathlib import Path
import pytest
from constraint_recovery.agreement import compare_annotations,partition_metrics
from constraint_recovery.cli import main
from constraint_recovery.model import DiagramError
from constraint_recovery.agreement_view import comparison_page

ROOT=Path(__file__).parents[1]


def original():
    return json.loads((ROOT/'examples/compound.annotation.agent.json').read_text())


def renamed(data):
    value=deepcopy(data);mapping={o['id']:'other_'+o['id'] for o in value['objects']}
    for obj in value['objects']:obj['id']=mapping[obj['id']]
    for relation in value['relations']:
        relation['objects']=[mapping[k] for k in relation['objects']]
        if relation.get('connector'):relation['connector']=mapping[relation['connector']]
    return value


def test_object_id_permutations_do_not_change_group_role_or_positive_relation_agreement():
    left=original();result=compare_annotations(left,renamed(left))
    assert result['coverage']['joint_fraction']==1
    assert result['grouping']['adjusted_rand']==1 and result['grouping']['variation_of_information_bits']==0
    assert result['roles']['agreement_on_joint_domain']==1
    assert result['relations']['positive_labels']['positive_label_jaccard']==1
    assert result['relations']['connector_bindings']['positive_label_jaccard']==1
    assert result['reviews']['independence_verified'] is False


def test_adjusted_rand_on_a_small_analytic_contingency_table():
    result=partition_metrics(dict(enumerate([0,0,0,1,1])),dict(enumerate([0,0,1,1,1])))
    assert result['adjusted_rand']==pytest.approx(1/6)
    assert result['variation_of_information_bits']==pytest.approx(.8*math.log2(1.5)+.2*math.log2(9))


def test_split_group_is_not_hidden_by_soft_object_matching():
    left=original();right=renamed(left)
    decoder=next(o for o in right['objects'] if o['id']=='other_decoder')
    labels=decoder['parts'][1:];decoder['parts']=decoder['parts'][:1]
    right['objects'].append(dict(id='label_only',name='Constructed split',role='text',status='confirmed',parts=labels))
    result=compare_annotations(left,right)
    assert result['roles']['agreement_on_joint_domain']==pytest.approx(.8)
    assert result['grouping']['adjusted_rand']==pytest.approx(28/33)
    assert result['object_correspondence']['unmatched_right']
    assert result['relations']['left']['unscorable_confirmed']==1
    assert result['relations']['positive_labels']['positive_label_jaccard'] is None


def test_abstaining_on_a_difficult_object_cannot_claim_full_coverage():
    left=original();right=deepcopy(left)
    next(o for o in right['objects'] if o['id']=='decoder').update(status='unknown',role='unknown')
    result=compare_annotations(left,right)
    assert result['coverage']['joint_confirmed']==7 and result['coverage']['total_primitives']==10
    assert result['coverage']['joint_fraction']==.7
    assert result['grouping']['adjusted_rand']==1  # Conditional domain only.
    assert result['relations']['right']['unscorable_confirmed']==1
    assert result['relations']['positive_labels']['positive_label_jaccard'] is None


def test_unknown_only_and_singleton_domains_do_not_receive_perfect_grouping_scores():
    left=original()
    for o in left['objects']:o.update(status='unknown',role='unknown')
    result=compare_annotations(left,deepcopy(left))
    assert result['coverage']['joint_confirmed']==0
    assert result['roles']['agreement_on_joint_domain'] is None
    assert result['grouping']['adjusted_rand'] is None
    assert partition_metrics({'p':'one'},{'p':'different'})['adjusted_rand'] is None


def test_relation_symmetry_is_separate_from_directed_endpoint_order():
    left=original();left['relations'].append(dict(kind='align_x',objects=['encoder','decoder'],status='confirmed',rationale='Constructed fixture'))
    right=renamed(left)
    for relation in right['relations']:relation['objects'].reverse()
    result=compare_annotations(left,right)
    assert result['relations']['positive_labels']['intersection']==1
    assert result['relations']['positive_labels']['union']==3
    assert result['relations']['connector_bindings']['positive_label_jaccard'] is None


def test_duplicate_positive_labels_do_not_inflate_set_overlap():
    left=original();right=deepcopy(left);right['relations'].append(deepcopy(right['relations'][0]))
    result=compare_annotations(left,right)
    assert result['relations']['right']['duplicate_comparable_declarations']==1
    assert result['relations']['positive_labels']['intersection']==1


def test_missing_connector_binding_is_unscorable_instead_of_false():
    left=original();right=deepcopy(left);right['relations'][0]['connector']=None
    result=compare_annotations(left,right)
    assert result['relations']['positive_labels']['positive_label_jaccard']==1
    assert result['relations']['right']['unscorable_connector_bindings']==1
    assert result['relations']['connector_bindings']['positive_label_jaccard'] is None


def test_one_sided_positive_is_an_omission_or_disagreement_not_an_accuracy_label():
    left=original();right=deepcopy(left);right['relations']=[]
    result=compare_annotations(left,right)['relations']['positive_labels']
    assert result['positive_label_jaccard']==0 and len(result['left_only'])==1
    assert 'not established false' in result['scope']


def test_source_and_declared_inventory_mismatches_are_rejected():
    left=original();right=deepcopy(left);right['source_sha256']='b'*64
    with pytest.raises(DiagramError,match='different source'):
        compare_annotations(left,right)
    right=deepcopy(left);right['objects'][0]['parts'][0]='unmeasured-part'
    with pytest.raises(DiagramError,match='inventories differ'):
        compare_annotations(left,right)


def test_source_and_measurement_checks_remain_explicit():
    left=original();source=(ROOT/'examples/compound.svg').read_text()
    measured=dict(source_sha256=left['source_sha256'],primitives=[dict(location=p) for o in left['objects'] for p in o['parts']])
    result=compare_annotations(left,renamed(left),source,measured)
    assert result['source_hash_checked'] and result['primitive_inventory_checked']
    measured['primitives'][0]['location']='absent'
    with pytest.raises(DiagramError,match='Unknown primitive'):
        compare_annotations(left,left,source,measured)


def test_comparison_cli_preserves_inputs_and_writes_a_local_report(tmp_path,monkeypatch):
    import sys
    left=tmp_path/'a.json';right=tmp_path/'b.json';output=tmp_path/'comparison.json'
    left.write_text(json.dumps(original()));right.write_text(json.dumps(renamed(original())))
    monkeypatch.setattr(sys,'argv',['constraint-recovery','compare-annotations',str(left),str(right),'--output',str(output)])
    assert main()==0
    assert json.loads(output.read_text())['reviews']['independence_verified'] is False
    original_bytes=left.read_bytes()
    monkeypatch.setattr(sys,'argv',['constraint-recovery','compare-annotations',str(left),str(right),'--output',str(left)])
    assert main()==2
    assert left.read_bytes()==original_bytes


def test_portable_report_escapes_untrusted_labels_without_changing_json_values():
    left=original();left['objects'][0]['name']='</script><script>window.BAD=true</script>'
    result=compare_annotations(left,renamed(left));page=comparison_page(result,left,renamed(left))
    payload=page.split('<script id="data" type="application/json">',1)[1].split('</script>',1)[0]
    assert json.loads(payload)['left']['objects'][0]['name']==left['objects'][0]['name']
    assert '<script>window.BAD=true</script>' not in page


def test_source_overlay_report_requires_bound_browser_projection():
    left=original();source=(ROOT/'examples/compound.svg').read_text()
    result=compare_annotations(left,left,source)
    with pytest.raises(DiagramError,match='browser measurements'):
        comparison_page(result,left,left,source)


def test_html_sidecar_cannot_overwrite_an_annotation_input(tmp_path,monkeypatch):
    import sys
    left=tmp_path/'review.html';right=tmp_path/'other.json';output=tmp_path/'review.json'
    left.write_text(json.dumps(original()));right.write_text(json.dumps(renamed(original())))
    before=left.read_bytes()
    monkeypatch.setattr(sys,'argv',['constraint-recovery','compare-annotations',str(left),str(right),'--output',str(output),'--html'])
    assert main()==2 and left.read_bytes()==before and not output.exists()
