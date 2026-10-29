import math
import random
import pytest
from constraint_recovery.channel import route_parallel_channel
from constraint_recovery.edge_check import parallel_contacts,segment_contact
from constraint_recovery.model import DiagramError


def fixture():
    starts=[40,80,120,160,200,240,280];ends=[176,180,184,188,192,196,200]
    nets={str(i):dict(start=[a,70],end=[b,250],source_stub=[a,128],target_stub=[b,222],axis=1,target_axis=1) for i,(a,b) in enumerate(zip(starts,ends))}
    return nets,{'s':[20,20,320,120],'t':[160,230,360,300]},[500,350]


@pytest.mark.parametrize('orientation',['down','up','right','left'])
def test_ordered_channel_preserves_distinct_anchors_without_external_shaft_contacts(orientation):
    nets,boxes,canvas=fixture()
    if orientation!='down':
        height=canvas[1]
        def coordinate(p):
            if orientation=='up':return [p[0],height-p[1]]
            if orientation=='right':return [p[1],p[0]]
            return [height-p[1],p[0]]
        for net in nets.values():
            for name in ['start','end','source_stub','target_stub']:net[name]=coordinate(net[name])
            net['axis']=net['target_axis']=1 if orientation=='up' else 0
        for key,b in boxes.items():
            corners=[coordinate([x,y]) for x in [b[0],b[2]] for y in [b[1],b[3]]]
            boxes[key]=[min(p[0] for p in corners),min(p[1] for p in corners),max(p[0] for p in corners),max(p[1] for p in corners)]
        if orientation in {'left','right'}:canvas=canvas[::-1]
    routes,evidence=route_parallel_channel(nets,boxes,canvas,'s','t')
    assert routes is not None and evidence['candidate']
    for key,path in routes.items():
        assert path[0]==nets[key]['start'] and path[-1]==nets[key]['end']
        assert len(path)<=4
    assert parallel_contacts(routes,list(boxes.values()))['contact_pairs']==0


def test_order_cycle_declines_only_this_candidate_family():
    nets,boxes,canvas=fixture()
    a,b=nets['0'],nets['1']
    a['end'][0]=b['start'][0];b['end'][0]=a['start'][0]
    a['target_stub'][0]=a['end'][0];b['target_stub'][0]=b['end'][0]
    routes,evidence=route_parallel_channel({'a':a,'b':b},boxes,canvas,'s','t')
    assert routes is None and 'Cyclic order' in evidence['reason']


def test_channel_refuses_coincident_ports_tight_tracks_and_obstacles():
    nets,boxes,canvas=fixture()
    nets['1']['start'][0]=nets['0']['start'][0]
    assert 'Coincident' in route_parallel_channel(nets,boxes,canvas,'s','t')[1]['reason']
    nets,boxes,canvas=fixture()
    for net in nets.values():net['target_stub'][1]=150
    assert route_parallel_channel(nets,boxes,canvas,'s','t')[0] is None
    nets,boxes,canvas=fixture();boxes['wall']=[0,150,500,170]
    assert 'protected clearance' in route_parallel_channel(nets,boxes,canvas,'s','t')[1]['reason']


@pytest.mark.parametrize('p,q,a,b,boxes,points,length',[
    ([0,0],[10,0],[5,-5],[5,5],[],1,0),
    ([0,0],[10,0],[5,0],[15,0],[],0,5),
    ([10,0],[0,0],[15,0],[5,0],[],0,5),
    ([0,0],[10,0],[5,0],[15,0],[[0,-1,7,1]],0,3),
    ([0,0],[10,0],[5,0],[15,0],[[0,-1,8,1],[7,-1,9,1]],0,1),
    ([0,0],[10,0],[5,-5],[5,5],[[4,-1,6,1]],0,0),
    ([0,0],[5,0],[5,0],[10,0],[],1,0),
    ([0,0],[10,0],[0,.01],[10,.01],[],0,0),
    ([0,0],[10,10],[0,10],[10,0],[],1,0),
    ([0,0],[10,10],[5,5],[15,15],[],0,math.sqrt(50)),
])
def test_independent_contact_checker_on_analytic_segments(p,q,a,b,boxes,points,length):
    observed_points,observed_length=segment_contact(p,q,a,b,boxes)
    assert observed_points==points and observed_length==pytest.approx(length)


def test_contact_summary_counts_pairs_instead_of_calling_each_bend_a_new_connection():
    paths={'a':[[0,0],[10,0],[10,10]],'b':[[5,-5],[5,0],[10,0],[10,5]]}
    result=parallel_contacts(paths,[])
    assert result['contact_pairs']==1 and result['shared_segment_pairs']==1
    assert result['pairwise_shared_length']==pytest.approx(10)


def test_seeded_order_preserving_port_families_have_no_external_contacts():
    rng=random.Random(971)
    for count in range(2,11):
        for _ in range(10):
            starts=sorted(rng.sample(range(20,380),count));ends=sorted(rng.sample(range(20,380),count))
            nets={str(i):dict(start=[a,50],end=[b,350],source_stub=[a,108],target_stub=[b,292],axis=1,target_axis=1) for i,(a,b) in enumerate(zip(starts,ends))}
            boxes={'s':[0,0,400,100],'t':[0,300,400,400]}
            routes,evidence=route_parallel_channel(nets,boxes,[400,400],'s','t')
            assert routes is not None,evidence
            assert parallel_contacts(routes,list(boxes.values()))['contact_pairs']==0


def test_contact_budget_cannot_return_a_partial_clean_result():
    paths={'a':[[0,0],[10,0],[10,10]],'b':[[5,-5],[5,0],[10,0],[10,5]]}
    with pytest.raises(DiagramError,match='no partial separation'):
        parallel_contacts(paths,[],max_comparisons=1)
