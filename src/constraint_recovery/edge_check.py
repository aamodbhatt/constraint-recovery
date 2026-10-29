"""Independent contacts between serialized shaft segments outside node boxes.

No routing/search calls. Centerline geometry only; stroke/head extents and
contacts hidden inside accepted endpoint envelopes are outside this scope.
"""
import math
from .model import DiagramError

EPS=1e-6


def _cross(a,b):
    return a[0]*b[1]-a[1]*b[0]


def _inside(p,box):
    return box[0]-EPS<=p[0]<=box[2]+EPS and box[1]-EPS<=p[1]<=box[3]+EPS


def _box_interval(p,r,box):
    low,high=0.,1.
    for axis in range(2):
        if abs(r[axis])<EPS:
            if not box[axis]-EPS<=p[axis]<=box[axis+2]+EPS:return None
        else:
            a,b=sorted([(box[axis]-p[axis])/r[axis],(box[axis+2]-p[axis])/r[axis]])
            low=max(low,a);high=min(high,b)
            if low>high+EPS:return None
    return low,high


def _outside_length(p,q,boxes):
    r=[q[i]-p[i] for i in range(2)];length=math.hypot(*r)
    if length<EPS:return 0.
    spans=sorted(v for b in boxes if (v:=_box_interval(p,r,b)) is not None)
    covered=0.;cursor=0.
    for a,b in spans:
        a=max(0.,a);b=min(1.,b)
        if b>max(a,cursor):covered+=b-max(a,cursor)
        cursor=max(cursor,b)
    return max(0.,1-covered)*length


def segment_contact(p,q,a,b,boxes=()):
    """Return external point-contact and positive shared-length observations."""
    r=[q[i]-p[i] for i in range(2)];s=[b[i]-a[i] for i in range(2)]
    nr,ns=math.hypot(*r),math.hypot(*s)
    if min(nr,ns)<EPS:return 0,0.
    offset=[a[i]-p[i] for i in range(2)]
    denominator=_cross(r,s)
    if abs(denominator)>EPS*max(1.,nr*ns):
        t,u=_cross(offset,s)/denominator,_cross(offset,r)/denominator
        if not -EPS<=t<=1+EPS or not -EPS<=u<=1+EPS:return 0,0.
        v=[p[i]+t*r[i] for i in range(2)]
        return (0 if any(_inside(v,box) for box in boxes) else 1),0.
    if abs(_cross(offset,r))>EPS*max(1.,nr*math.hypot(*offset)):
        return 0,0.
    rr=nr*nr
    t0=sum(offset[i]*r[i] for i in range(2))/rr
    t1=t0+sum(s[i]*r[i] for i in range(2))/rr
    lo,hi=max(0.,min(t0,t1)),min(1.,max(t0,t1))
    if lo>hi+EPS:return 0,0.
    start=[p[i]+lo*r[i] for i in range(2)]
    end=[p[i]+hi*r[i] for i in range(2)]
    if math.dist(start,end)<EPS:
        return (0 if any(_inside(start,box) for box in boxes) else 1),0.
    return 0,_outside_length(start,end,boxes)


def parallel_contacts(paths,boxes,max_comparisons=2_000_000):
    """Pair counts avoid treating each bend's duplicated point as a new pair."""
    pairs=[];keys=sorted(paths);work=0
    for i,key in enumerate(keys):
        for other in keys[i+1:]:
            work+=(len(paths[key])-1)*(len(paths[other])-1)
            if work>max_comparisons:
                raise DiagramError('Parallel shaft contact check exceeds its segment-comparison budget; no partial separation result accepted')
            points=0;length=0.
            for p,q in zip(paths[key],paths[key][1:]):
                for a,b in zip(paths[other],paths[other][1:]):
                    count,shared=segment_contact(p,q,a,b,boxes)
                    points+=count;length+=shared
            if points or length>EPS:
                pairs.append({'connectors':[key,other],'point_contact_observations':points,'shared_length':length})
    return {'connectors':len(paths),'contact_pairs':len(pairs),
            'segment_pair_comparisons':work,
            'shared_segment_pairs':sum(p['shared_length']>EPS for p in pairs),
            'pairwise_shared_length':sum(p['shared_length'] for p in pairs),'pairs':pairs,
            'scope':'Serialized shaft centerlines outside the two accepted endpoint envelopes; excludes strokes, heads, unchanged edges and contacts inside those envelopes'}
