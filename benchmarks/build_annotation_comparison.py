"""Scripted comparison fixtures, not independent annotators or real agreement data."""
from copy import deepcopy
import json
from pathlib import Path
from constraint_recovery.agreement import compare_annotations
from constraint_recovery.agreement_view import comparison_page

ROOT=Path(__file__).resolve().parents[1]


def rename(value):
    result=deepcopy(value);mapping={o['id']:'variant_'+o['id'] for o in result['objects']}
    for obj in result['objects']:obj['id']=mapping[obj['id']]
    for relation in result['relations']:
        relation['objects']=[mapping[key] for key in relation['objects']]
        if relation.get('connector'):relation['connector']=mapping[relation['connector']]
    result['review'].update(annotator='scripted annotation perturbation',
        evidence='Constructed variation of the same authored program annotation to exercise comparison behavior. Not a second independent reviewer or human ground truth.')
    return result


def main():
    original=json.loads((ROOT/'examples/compound.annotation.agent.json').read_text())
    source=(ROOT/'examples/compound.svg').read_text()
    measured=json.loads((ROOT/'artifacts/comparison-geometry.json').read_text())
    aliases=rename(original)
    split=rename(original);obj=next(o for o in split['objects'] if o['id']=='variant_decoder')
    text=obj['parts'][1:];obj['parts']=obj['parts'][:1]
    split['objects'].append(dict(id='variant_decoder_labels',name='Scripted split: text separate from card',role='text',status='confirmed',parts=text))
    partial=rename(original);next(o for o in partial['objects'] if o['id']=='variant_decoder').update(status='unknown',role='unknown')
    folder=ROOT/'examples/annotation-comparison';folder.mkdir(parents=True,exist_ok=True)
    variants={'renamed':aliases,'split':split,'partial':partial}
    reports={}
    for name,value in variants.items():
        (folder/f'{name}.agent.json').write_text(json.dumps(value,indent=2)+'\n')
        reports[name]=compare_annotations(original,value,source,measured)
    report=dict(schema_version=1,demonstration_scope='Scripted perturbations of one authored program annotation. No independent reviewers, real inter-annotator agreement study or human ground truth.',
                source='examples/compound.svg',independent_human_annotations=0,cases=reports)
    (ROOT/'results/annotation-comparison-fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
    page=comparison_page(reports['split'],original,split,source,measured)
    banner='<div class="domain" style="margin-bottom:24px"><strong>Scripted demonstration · authored MIT fixture.</strong> The right label set is a constructed split of the same program annotation. These are not two independent reviewers and no human agreement result is claimed.</div>'
    (ROOT/'docs/demo/annotation-comparison.html').write_text(page.replace('<main>','<main>'+banner,1))
    print(json.dumps({name:dict(joint_coverage=r['coverage']['joint_fraction'],grouping_adjusted_rand=r['grouping']['adjusted_rand'],role_agreement=r['roles']['agreement_on_joint_domain'],unscorable_left_relations=r['relations']['left']['unscorable_confirmed']) for name,r in reports.items()},indent=2))


if __name__=='__main__':main()
