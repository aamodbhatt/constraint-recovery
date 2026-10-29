"""Coverage-aware annotation comparison, without choosing a gold reviewer.

Grouping metrics are permutation invariant. Unknowns remain excluded with their
denominators reported. A missing positive relation is not assumed to be false.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
import numpy as np
from scipy.optimize import linear_sum_assignment
from .annotation import validate_annotation
from .model import DiagramError

SYMMETRIC={'align_x','align_y','group'}


def _ratio(a,b):
    return a/b if b else None


def _inventory(annotation):
    return {p for o in annotation['objects'] for p in o['parts']}|set(annotation['coverage']['unassigned_parts'])


def _confirmed(annotation):
    return {o['id']:o for o in annotation['objects'] if o['status']=='confirmed' and o['role']!='unknown'}


def partition_metrics(left,right):
    """Metrics on two complete partitions of the supplied shared domain."""
    if set(left)!=set(right):
        raise DiagramError('Grouping metrics require the same primitive domain')
    n=len(left);cells=Counter((left[p],right[p]) for p in left)
    rows=Counter(left.values());columns=Counter(right.values())
    choose=lambda value:value*(value-1)//2
    both=sum(choose(value) for value in cells.values())
    left_pairs=sum(choose(value) for value in rows.values())
    right_pairs=sum(choose(value) for value in columns.values())
    total=choose(n)
    ari=rand=vi=None
    if total:
        expected=Fraction(left_pairs*right_pairs,total)
        denominator=Fraction(left_pairs+right_pairs,2)-expected
        ari=float((both-expected)/denominator) if denominator else 1.
        rand=1-(left_pairs+right_pairs-2*both)/total
        vi=sum(count/n*math.log2(rows[a]*columns[b]/(count*count)) for (a,b),count in cells.items())
    return dict(primitives=n,primitive_pairs=total,left_same_pairs=left_pairs,right_same_pairs=right_pairs,
                both_same_pairs=both,adjusted_rand=ari,rand=rand,variation_of_information_bits=vi,
                scope='Jointly confirmed primitive domain only; report joint coverage alongside these grouping metrics')


def _object_matches(left,right):
    if max(len(left),len(right))>500:
        raise DiagramError('Object comparison exceeds its 500-confirmed-object budget')
    left_keys,right_keys=sorted(left),sorted(right)
    sets_l={key:set(o['parts']) for key,o in left.items()};sets_r={key:set(o['parts']) for key,o in right.items()}
    matrix=np.zeros((len(left_keys),len(right_keys)))
    for i,a in enumerate(left_keys):
        for j,b in enumerate(right_keys):
            intersection=len(sets_l[a]&sets_r[b]);union=len(sets_l[a]|sets_r[b])
            matrix[i,j]=intersection/union
    matched=[]
    if matrix.size:
        rows,cols=linear_sum_assignment(matrix,maximize=True)
        for i,j in zip(rows,cols):
            value=float(matrix[i,j])
            if not value:
                continue
            a,b=left_keys[i],right_keys[j]
            tied_row=sum(abs(float(v)-value)<1e-12 for v in matrix[i])>1
            tied_col=sum(abs(float(v)-value)<1e-12 for v in matrix[:,j])>1
            matched.append(dict(left=a,right=b,iou=value,intersection_parts=len(sets_l[a]&sets_r[b]),
                                union_parts=len(sets_l[a]|sets_r[b]),exact_parts=sets_l[a]==sets_r[b],
                                roles_equal=left[a]['role']==right[b]['role'],local_iou_tie=tied_row or tied_col))
    matched_l={m['left'] for m in matched};matched_r={m['right'] for m in matched}
    return dict(left_objects=len(left),right_objects=len(right),matches=matched,
                unmatched_left=[k for k in left_keys if k not in matched_l],unmatched_right=[k for k in right_keys if k not in matched_r],
                overlap_sum=sum(m['iou'] for m in matched),
                overlap_per_larger_object_count=_ratio(sum(m['iou'] for m in matched),max(len(left),len(right))),
                scope='Maximum-total-IoU correspondence on full confirmed part sets, ignoring role for assignment. Tied assignments are not semantic adjudication; unmatched objects remain in the denominator')


def _canonical(relation,mapping):
    ids=[mapping[key] for key in relation['objects']]
    if relation['kind'] in SYMMETRIC:ids.sort()
    return relation['kind'],tuple(ids)


def _positive_sets(annotation,mapping):
    confirmed=[r for r in annotation['relations'] if r['status']=='confirmed']
    comparable=[];unscorable=[];bindings=[];binding_unscorable=[]
    for index,relation in enumerate(confirmed):
        if any(key not in mapping for key in relation['objects']):
            unscorable.append(index);continue
        key=_canonical(relation,mapping);comparable.append(key)
        if relation['kind']=='directed_edge':
            connector=relation.get('connector')
            if connector is None or connector not in mapping:binding_unscorable.append(index)
            else:bindings.append((key,mapping[connector]))
    return dict(declared_confirmed=len(confirmed),comparable_declarations=len(comparable),
                unscorable_confirmed=len(unscorable),duplicate_comparable_declarations=len(comparable)-len(set(comparable)),
                positive_labels=set(comparable),connector_bindings=set(bindings),unscorable_connector_bindings=len(binding_unscorable),
                ambiguous_relations=sum(r['status']=='ambiguous' for r in annotation['relations']),
                unknown_relations=sum(r['status']=='unknown' for r in annotation['relations']))


def _overlap(a,b):
    return dict(intersection=len(a&b),union=len(a|b),left_only=sorted(a-b),right_only=sorted(b-a),
                positive_label_jaccard=_ratio(len(a&b),len(a|b)),
                scope='Overlap of declared comparable positive labels. Missing/one-sided labels are omissions or disagreements to review, not established false positives or negatives')


def compare_annotations(left,right,source=None,measurements=None):
    digest=hashlib.sha256(source.encode('utf-8')).hexdigest() if source is not None else None
    validate_annotation(left,digest,measurements);validate_annotation(right,digest,measurements)
    if left['source_sha256']!=right['source_sha256']:
        raise DiagramError('Annotations belong to different source SVGs')
    universe=_inventory(left)
    if universe!=_inventory(right):
        raise DiagramError('Declared primitive inventories differ; do not silently compare their intersection')
    if len(universe)>5000:
        raise DiagramError('Annotation comparison exceeds its 5000-primitive budget')
    known_l,known_r=_confirmed(left),_confirmed(right)
    owner_l={p:key for key,o in known_l.items() for p in o['parts']}
    owner_r={p:key for key,o in known_r.items() for p in o['parts']}
    joint=set(owner_l)&set(owner_r)
    disagreement=[dict(part=p,left_role=known_l[owner_l[p]]['role'],right_role=known_r[owner_r[p]]['role'])
                  for p in sorted(joint) if known_l[owner_l[p]]['role']!=known_r[owner_r[p]]['role']]
    grouping=partition_metrics({p:owner_l[p] for p in joint},{p:owner_r[p] for p in joint})
    # Relation overlap is deliberately stricter than the soft IoU diagnostic:
    # full object part sets and roles must match exactly before comparing labels.
    signatures={(tuple(sorted(o['parts'])),o['role']):key for key,o in known_l.items()}
    mapping_r={key:signatures[(tuple(sorted(o['parts'])),o['role'])] for key,o in known_r.items()
               if (tuple(sorted(o['parts'])),o['role']) in signatures}
    mapping_l={key:key for key in mapping_r.values()}
    labels_l,labels_r=_positive_sets(left,mapping_l),_positive_sets(right,mapping_r)
    positive=_overlap(labels_l.pop('positive_labels'),labels_r.pop('positive_labels'))
    bindings_l,bindings_r=labels_l.pop('connector_bindings'),labels_r.pop('connector_bindings')
    joint_grounded_edges={key for key,_ in bindings_l}&{key for key,_ in bindings_r}
    bindings=_overlap({item for item in bindings_l if item[0] in joint_grounded_edges},
                      {item for item in bindings_r if item[0] in joint_grounded_edges})
    bindings.update(joint_grounded_edge_labels=len(joint_grounded_edges),
                    left_excluded_grounded_labels=sum(key not in joint_grounded_edges for key,_ in bindings_l),
                    right_excluded_grounded_labels=sum(key not in joint_grounded_edges for key,_ in bindings_r),
                    scope='Only jointly declared edge labels with exact grounded connector objects on both sides. Missing/unmatched bindings remain unscorable, not false.')
    geometry=[]
    for right_id,left_id in sorted(mapping_r.items()):
        a=known_l[left_id].get('connector_geometry');b=known_r[right_id].get('connector_geometry')
        if a is not None or b is not None:
            geometry.append(dict(left=left_id,right=right_id,left_present=a is not None,right_present=b is not None,
                                 fields_identical=a==b if a is not None and b is not None else None))
    annotation_hashes={side:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest() for side,value in [('left',left),('right',right)]}
    return dict(schema_version=1,source_sha256=left['source_sha256'],annotation_sha256=annotation_hashes,source_hash_checked=digest is not None,
        primitive_inventory_checked=measurements is not None,
        reviews=dict(left=left['review'],right=right['review'],independence_verified=False),
        coverage=dict(total_primitives=len(universe),left_confirmed=len(owner_l),right_confirmed=len(owner_r),joint_confirmed=len(joint),
                      joint_fraction=_ratio(len(joint),len(universe)),left_only_confirmed=len(set(owner_l)-joint),
                      right_only_confirmed=len(set(owner_r)-joint),neither_confirmed=len(universe-(set(owner_l)|set(owner_r)))),
        roles=dict(comparable_primitives=len(joint),equal=len(joint)-len(disagreement),
                   agreement_on_joint_domain=_ratio(len(joint)-len(disagreement),len(joint)),disagreements=disagreement),
        grouping=grouping,object_correspondence=_object_matches(known_l,known_r),
        exact_part_and_role_correspondences=[dict(left=a,right=b) for b,a in sorted(mapping_r.items())],
        relations=dict(left=labels_l,right=labels_r,positive_labels=positive,connector_bindings=bindings),
        explicit_connector_geometry=geometry,
        limitations=['No reviewer is treated as gold and annotator identity/independence is not verified',
                     'Unknown, ambiguous and unassigned primitive roles are excluded with coverage reported',
                     'IoU matching is a diagnostic; relation comparison requires exact full-part and role correspondence',
                     'Positive-label overlap is not relation accuracy; unlisted relations are not established negatives',
                     'Empty/unscorable denominators return null rather than perfect agreement'])
