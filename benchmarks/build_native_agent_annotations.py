"""Materialize explicitly agent-authored pilot labels; never human ground truth.

Selectors below transcribe a visual/source review of the five frozen figures.
This is not an object-recovery model or an independent annotation procedure.
"""
import json
from pathlib import Path
from constraint_recovery.annotation import validate_annotation

ROOT=Path(__file__).resolve().parents[1]


def build(entry):
    measured=json.loads((ROOT/'.cache/native-pilot/geometry'/f'{entry["id"]}.json').read_text())
    inventory=[p['location'] for p in measured['primitives']]
    objects=[];relations=[]
    def obj(key,name,parts,role='node',status='confirmed',**extra):
        objects.append(dict(id=key,name=name,parts=parts,role=role,status=status,**extra))
    def group(prefix):
        return [p for p in inventory if p.startswith(prefix)]
    def edge(a,b,key,parts,geometry=None):
        obj(key,key,parts,'connector',**({'connector_geometry':geometry} if geometry else {}))
        relations.append(dict(kind='directed_edge',objects=[a,b],connector=key,status='confirmed',
                              rationale='Agent interpretation of the original rendered connection and source geometry; not independently verified author intent.'))
    name=entry['id']
    if name=='distill-rnn-basic':
        obj('band','Repeated-cell background band',group('svg/g[2]/'),'background')
        for i,(root,labels,ports) in enumerate([(3,[8,9],[21,22]),(4,[10,11],[23,24]),(5,[12,13],[25,26]),(6,[14,15],[27,28]),(7,[31,32],[34,35])]):
            parts=group(f'svg/g[{root}]/')+[f'svg/text[{n}]' for n in labels]
            parts+=sum([group(f'svg/g[{n}]/') for n in ports],[])
            obj(f'step{i}',f'Timestep {i}, including input/output labels and internal ports',parts)
        obj('commentary','Unchanged explanatory headings',sum([group(f'svg/g[{n}]/') for n in [16,17,18,19,33]],[]),'text')
        for i,(n,tip) in enumerate([(20,138.67),(29,270.67),(30,402.67),(36,533.92)]):
            shaft,head=f'svg/g[{n}]/line[0]',f'svg/g[{n}]/path[1]'
            edge(f'step{i}',f'step{i+1}',f'state{i}',[shaft,head],
                 dict(shaft=shaft,direction='forward',end_head=dict(part=head,tip=[tip,66.43])))
        moves=[{'step2':[12,0]},{'step2':[-6,0]}]
    elif name=='distill-rnn-read':
        inputs=[f'svg/use[{n}]' for n in [3,4]]+sum([group(f'svg/g[{n}]/') for n in [6,7,9,10]],[])
        obj('inputs','Attention and memory arrays, with their labels',inputs)
        out=[f'svg/use[5]']+sum([group(f'svg/g[{n}]/') for n in [8,13,14,15]],[])
        obj('readout','Read result, equation, leader and explanatory label',out)
        obj('pointer','Unchanged attention pointer',[f'svg/use[11]'],'decoration')
        obj('explanation','Unchanged explanation paragraph',group('svg/g[12]/'),'text')
        for i in range(7):
            shaft=f'svg/g[2]/path[{i}]'
            edge('inputs','readout',f'weight{i}',[shaft],dict(shaft=shaft,direction='forward'))
        moves=[{'readout':[24,8]},{'readout':[-12,-4]}]
    elif name=='distill-rnn-memory':
        parts=[f'svg/use[{i}]' for i in [4,54,55,56,57,67]]
        obj('memory1','Second memory-array state',parts)
        obj('context','Unresolved read/write paths and surrounding recurrent structure',[p for p in inventory if p not in parts],'unknown','unknown')
        relations.append(dict(kind='directed_edge',objects=['context','memory1'],connector=None,status='unknown',
                              rationale='The read/write links use separate curved shafts and heads. Their grouping/attachment has not been fully resolved; decline this move rather than omit the uncertainty.'))
        moves=[{'memory1':[0,-8]},{'memory1':[0,4]}]
    elif name=='distill-graph-tasks':
        top=group('svg/g[4]/g[0]/');connector='svg/g[4]/path[1]'
        obj('input_graph','Input graph with node values and letter labels',top)
        obj('tasks','Complete task-example panel',[p for p in inventory if p not in top+[connector]])
        edge('input_graph','tasks','task_mapping',[connector])
        moves=[{'input_graph':[0,6]},{'input_graph':[-4,0]}]
    else:
        upper=group('svg/g[3]/g[9]/');lower=group('svg/g[3]/g[11]/')
        top_input=[f'svg/g[3]/rect[{n}]' for n in range(7)]+[f'svg/g[3]/text[{n}]' for n in range(17,23)]+['svg/g[3]/path[8]']
        lower_input=group('svg/g[4]/')+group('svg/g[3]/g[12]/')+[f'svg/g[3]/path[{n}]' for n in [13,14,15]]
        for key,label,parts in [('top_input','Vector and check mark',top_input),('top_mlp','Complete upper MLP',upper),('graph_input','Graph and question mark',lower_input),('bottom_mlp','Complete lower MLP',lower)]:
            obj(key,label,parts)
        edge('top_input','top_mlp','vector_mapping',['svg/g[3]/path[7]'])
        edge('graph_input','bottom_mlp','graph_mapping',['svg/g[3]/path[10]'])
        used={p for o in objects for p in o['parts']}
        remainder=[p for p in inventory if p not in used]
        if remainder:obj('unused_source_text','Unchanged empty source text',remainder,'unknown','unknown')
        moves=[{'top_input':[0,4],'top_mlp':[0,4]},{'top_input':[0,-2],'top_mlp':[0,-2]}]
    assigned=[p for o in objects for p in o['parts']]
    annotation=dict(schema_version=2,kind='diagram-annotation',diagram_id=name,source_url=entry['source_url'],
        source_sha256=entry['source_sha256'],license=entry['license'],split='development',
        review=dict(status='agent-reviewed',annotator_type='agent',annotator='Codex native-pilot development review',
                    evidence='Agent visually inspected the original render and source on 2026-10-30. Scripted selectors transcribe that interpretation; no author approval, independent human labels or automatic recovery claim.'),
        objects=objects,relations=relations,coverage=dict(total_primitives=len(inventory),assigned_primitives=len(assigned),unassigned_parts=[p for p in inventory if p not in assigned]))
    validate_annotation(annotation,entry['source_sha256'],measured)
    return annotation,dict(schema_version=1,figure=name,steps=moves,impossible={next(iter(moves[0])):[-10000,0]},
        scope='Frozen explicit translations selected before execution. Preserve uncertainty and every failed case; do not replace requests for success.')


if __name__=='__main__':
    folder=ROOT/'data/native-pilot/annotations';folder.mkdir(parents=True,exist_ok=True)
    requests=ROOT/'data/native-pilot/requests';requests.mkdir(parents=True,exist_ok=True)
    for entry in json.loads((ROOT/'data/native-pilot-selection.json').read_text())['cases']:
        annotation,request=build(entry)
        (folder/f'{entry["id"]}.agent.json').write_text(json.dumps(annotation,indent=2)+'\n')
        (requests/f'{entry["id"]}.json').write_text(json.dumps(request,indent=2)+'\n')
        print(entry['id'],len(annotation['objects']),len(annotation['relations']),annotation['coverage'])
