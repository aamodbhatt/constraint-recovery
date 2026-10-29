"""Bounded single-channel candidates using classical track-order constraints.

This is a narrow routing preference, not a novel channel router or a global
infeasibility proof. Cycles/blocked tracks fall back to the visibility search.
"""
import heapq
import math
from .check import segment_hits_rect
from .model import Node
from .routing import simplify

TOL=1e-7


def route_parallel_channel(nets,obstacles,canvas,source,target,clearance=8):
    """Route distinct ports of one source/target pair with three-segment nets.

    Each net supplies start/end, source/target escape stubs, and their axes.
    Returned evidence describes only this candidate family. The independent
    serialized checker, rather than this function, measures exported contacts.
    """
    def decline(reason):
        return None,{'algorithm':'ordered-channel','candidate':False,'reason':reason}
    if not 2<=len(nets)<=32:
        return decline('Channel candidate requires 2..32 parallel connectors')
    axis=next(iter(nets.values()))['axis']
    if axis not in {0,1} or any(n['axis']!=axis or n['target_axis']!=axis for n in nets.values()):
        return decline('Ports do not use a common opposing axis')
    first=next(iter(nets.values()))
    sign=1 if first['source_stub'][axis]>first['start'][axis] else -1
    cross_axis=1-axis
    for n in nets.values():
        if not all(len(n[k])==2 and all(math.isfinite(v) for v in n[k]) for k in ['start','end','source_stub','target_stub']):
            return decline('Missing finite channel geometry')
        if sign*(n['source_stub'][axis]-n['start'][axis])<=0 or sign*(n['end'][axis]-n['target_stub'][axis])<=0:
            return decline('Ports do not face each other through one channel')
    low=max(sign*n['source_stub'][axis] for n in nets.values())+clearance
    high=min(sign*n['target_stub'][axis] for n in nets.values())-clearance
    if high<low:
        return decline('No empty track band between endpoint escape regions')
    starts={k:n['start'][cross_axis] for k,n in nets.items()}
    ends={k:n['end'][cross_axis] for k,n in nets.items()}
    if any(abs(a-b)<=TOL for values in [starts,ends] for i,a in enumerate(values.values()) for b in list(values.values())[i+1:]):
        return decline('Coincident terminal columns need a different junction model')
    # u is signed travel through the channel; v runs across the ports. If a
    # source branch j lies in trunk i's span, i must be deeper than j. If a
    # target branch j lies in that span, i must be shallower than j.
    successors={k:set() for k in nets}
    for i in nets:
        a,b=sorted([starts[i],ends[i]])
        for j in nets:
            if i==j:
                continue
            if a-TOL<=starts[j]<=b+TOL:successors[j].add(i)
            if a-TOL<=ends[j]<=b+TOL:successors[i].add(j)
    degree={k:0 for k in nets}
    for items in successors.values():
        for k in items:degree[k]+=1
    ready=[k for k in nets if degree[k]==0];heapq.heapify(ready)
    ranks={k:0 for k in nets};visited=0
    while ready:
        k=heapq.heappop(ready);visited+=1
        for other in sorted(successors[k]):
            ranks[other]=max(ranks[other],ranks[k]+1)
            degree[other]-=1
            if degree[other]==0:heapq.heappush(ready,other)
    if visited!=len(nets):
        return decline('Cyclic order constraints in the three-segment channel family')
    spacing=max(clearance,1.)
    span=max(ranks.values())*spacing
    if low+span>high+TOL:
        return decline('Track-order depth exceeds the available channel band')
    offset=low+(high-low-span)/2
    routes={};width,height=canvas
    inflated={k:Node(k,b[0]-clearance,b[1]-clearance,b[2]-b[0]+2*clearance,b[3]-b[1]+2*clearance) for k,b in obstacles.items()}
    for key,n in nets.items():
        track=sign*(offset+ranks[key]*spacing)
        a=list(n['start']);b=list(n['end']);a[axis]=b[axis]=track
        points=simplify([n['start'],a,b,n['end']])
        if any(not -TOL<=x<=width+TOL or not -TOL<=y<=height+TOL for x,y in points):
            return decline('A channel candidate leaves the canvas')
        for j,(p,q) in enumerate(zip(points,points[1:])):
            for other,box in inflated.items():
                if (j==0 and other==source) or (j==len(points)-2 and other==target):
                    continue
                if segment_hits_rect(p,q,box):
                    return decline('A channel track intersects a protected clearance envelope')
        routes[key]=points
    return routes,{'algorithm':'ordered-channel','candidate':True,'axis':axis,'sign':sign,
                   'track_spacing':spacing,'ranks':ranks,'signed_track_offset':offset,
                   'order_constraints':[[a,b] for a in sorted(successors) for b in sorted(successors[a])],
                   'scope':'Candidate in a bounded three-segment family; not a global optimum or an infeasibility certificate'}
