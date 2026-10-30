"""Geometry-only binding baselines; source graphs are never an input here."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

NODE_WIDTH=16
NODE_HEIGHT=12
DIRECTION_WEIGHT=.25
TIE_TOLERANCE=1e-9
TAGS={'rect','circle','ellipse','polygon','path','line','polyline'}


def finite_vector(value,size):
    return isinstance(value,list) and len(value)==size and all(type(v) in {int,float} and math.isfinite(v) and abs(v)<=1e6 for v in value)


def validate_observations(data):
    if not isinstance(data,dict) or set(data)!={'schema_version','kind','canvas','primitives'} or data['schema_version']!=1 or data['kind']!='blind-primitive-geometry':
        raise ValueError('Geometry-only input cannot contain source or oracle fields')
    if not finite_vector(data['canvas'],2) or min(data['canvas'])<=0 or max(data['canvas'])>20000:
        raise ValueError('Invalid canvas')
    if not isinstance(data['primitives'],list) or len(data['primitives'])>5000:
        raise ValueError('Primitive budget exceeded')
    identifiers=set()
    for p in data['primitives']:
        if not isinstance(p,dict) or set(p)!={'id','tag','bounds','closed','filled','stroked','path'}:
            raise ValueError('Unexpected primitive field: semantic identifiers and hierarchy are excluded')
        if not isinstance(p['id'],str) or not re.fullmatch(r'p-[a-f0-9]{12}',p['id']) or p['id'] in identifiers:
            raise ValueError('Opaque primitive identifiers must be unique')
        identifiers.add(p['id'])
        if p['tag'] not in TAGS or not finite_vector(p['bounds'],4) or p['bounds'][0]>p['bounds'][2] or p['bounds'][1]>p['bounds'][3]:
            raise ValueError('Invalid primitive geometry')
        if any(type(p[k]) is not bool for k in ['closed','filled','stroked']):
            raise ValueError('Invalid primitive paint/closure flag')
        path=p['path']
        if path is not None and (not isinstance(path,dict) or set(path)!={'start','end','start_direction','end_direction'} or any(not finite_vector(v,2) for v in path.values())):
            raise ValueError('Invalid path endpoint geometry')
    return data


def boundary_distance(point,bounds):
    x,y=point;left,top,right,bottom=bounds
    dx=max(left-x,0,x-right);dy=max(top-y,0,y-bottom)
    return math.hypot(dx,dy) if dx or dy else min(x-left,right-x,y-top,bottom-y)


def choose_endpoint(point,toward,nodes,weight):
    norm=math.hypot(*toward)
    if not nodes:return dict(node=None,reason='no node candidates')
    if weight and norm<1e-9:return dict(node=None,reason='directionless endpoint')
    ranked=[]
    for node in nodes:
        left,top,right,bottom=node['bounds'];scale=math.sqrt((right-left)*(bottom-top))
        delta=[(left+right)/2-point[0],(top+bottom)/2-point[1]];distance=math.hypot(*delta)
        alignment=sum(a*b for a,b in zip(delta,toward))/max(distance*norm,1e-9)
        score=boundary_distance(point,node['bounds'])/scale+weight*(1-alignment)
        ranked.append((score,node['id']))
    ranked.sort()
    if len(ranked)>1 and abs(ranked[0][0]-ranked[1][0])<=TIE_TOLERANCE:
        return dict(node=None,reason='tied geometric candidates')
    return dict(node=ranked[0][1],score=ranked[0][0],margin=ranked[1][0]-ranked[0][0] if len(ranked)>1 else None)


def recover(data):
    validate_observations(data)
    nodes=sorted([p for p in data['primitives'] if p['tag'] in {'rect','circle','ellipse','polygon','path'} and p['closed'] and (p['filled'] or p['stroked']) and
        p['bounds'][2]-p['bounds'][0]>=NODE_WIDTH and p['bounds'][3]-p['bounds'][1]>=NODE_HEIGHT],key=lambda p:p['id'])
    shafts=sorted([p for p in data['primitives'] if p['tag'] in {'line','polyline','path'} and p['stroked'] and not p['filled'] and not p['closed'] and p['path'] and
        math.dist(p['path']['start'],p['path']['end'])>2],key=lambda p:p['id'])
    methods={}
    for name,weight in [('nearest_boundary',0),('tangent_aware',DIRECTION_WEIGHT)]:
        edges=[]
        for shaft in shafts:
            geometry=shaft['path']
            edges.append(dict(shaft=shaft['id'],source=choose_endpoint(geometry['start'],[-v for v in geometry['start_direction']],nodes,weight),
                target=choose_endpoint(geometry['end'],geometry['end_direction'],nodes,weight)))
        methods[name]=edges
    return dict(schema_version=1,kind='geometric-binding-predictions',node_candidates=[p['id'] for p in nodes],
        shaft_candidates=[p['id'] for p in shafts],methods=methods,
        configuration=dict(minimum_width=NODE_WIDTH,minimum_height=NODE_HEIGHT,direction_weight=DIRECTION_WEIGHT,tie_tolerance=TIE_TOLERANCE))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():parser.error('Prediction output cannot overwrite its observation input')
    with args.input.open('rb') as stream:raw=stream.read(8_000_001)
    if len(raw)>8_000_000:parser.error('Observation input exceeds eight MB')
    result=recover(json.loads(raw));result['observation_sha256']=hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
