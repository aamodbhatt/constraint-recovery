from copy import deepcopy
from dataclasses import replace
import itertools
import math
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from .model import DiagramError
from .typography import wrap, text_width
from .svg import route
from .check import segment_hits_rect


def reroute(edge, nodes, width, height,clearance=0):
    a,b = nodes[edge.source],nodes[edge.target]
    def ports(n):
        return [[n.x,n.y+n.height/2],[n.x+n.width,n.y+n.height/2],
                [n.x+n.width/2,n.y],[n.x+n.width/2,n.y+n.height]]
    candidates = []
    for start,end in itertools.product(ports(a),ports(b)):
        paths = [[start,end], [start,[start[0],end[1]],end], [start,[end[0],start[1]],end]]
        for n in nodes.values():
            for x in [n.x-10,n.x+n.width+10]:
                paths.append([start,[x,start[1]],[x,end[1]],end])
            for y in [n.y-10,n.y+n.height+10]:
                paths.append([start,[start[0],y],[end[0],y],end])
        for path in paths:
            if any(x<0 or y<0 or x>width or y>height for x,y in path):
                continue
            def blocked():
                for j,(p,q) in enumerate(zip(path,path[1:])):
                    for n in nodes.values():
                        pad = 0 if (n.id==edge.source and j==0) or (n.id==edge.target and j==len(path)-2) else clearance
                        box = replace(n,x=n.x-pad,y=n.y-pad,width=n.width+2*pad,height=n.height+2*pad)
                        if segment_hits_rect(p,q,box):
                            return True
                return False
            if not blocked():
                length = sum(math.dist(p,q) for p,q in zip(path,path[1:]))
                candidates.append((length+8*len(path),path))
    if not candidates:
        raise DiagramError(f"No collision-free connector found for {edge.id}; no edit exported")
    edge.points = min(candidates,key=lambda c:c[0])[1]


def edit(diagram, labels=None, width=None, height=None, font_size=None, gap=24, flow="free", time_limit=10,router="visibility"):
    diagram.validate()
    labels = labels or {}
    unknown = set(labels)-{n.id for n in diagram.nodes}
    if unknown:
        raise DiagramError(f"Unknown label targets: {sorted(unknown)}")
    d = deepcopy(diagram)
    d.width = diagram.width if width is None else width
    d.height = diagram.height if height is None else height
    if flow not in {"free","vertical","horizontal"} or gap < 0 or time_limit <= 0 or router not in {"visibility","candidates"}:
        raise DiagramError("Invalid layout options")
    for n in d.nodes:
        if n.id in labels:
            if not isinstance(labels[n.id], str):
                raise DiagramError("Replacement labels must be strings")
            n.label = labels[n.id]
        if font_size is not None:
            n.font_size = font_size
        d.validate()
        preferred = max(32,min(220,d.width-56,n.width-24))
        n.lines = wrap(n.label,n.font_size,preferred)
        n.width = max(n.width,max(text_width(s,n.font_size) for s in n.lines)+24)
        n.height = max(n.height,len(n.lines)*n.font_size*1.3+20)
    d.validate()
    count = len(d.nodes)
    if count > 40:
        raise DiagramError("This baseline supports at most 40 nodes")
    pairs = list(itertools.combinations(range(count),2))
    size = 4*count+4*len(pairs)
    objective = np.zeros(size)
    objective[2*count:4*count] = 1
    lower = np.zeros(size)
    upper = np.full(size,np.inf)
    integer = np.zeros(size)
    upper[4*count:] = 1
    integer[4*count:] = 1
    for i,n in enumerate(d.nodes):
        lower[i],lower[count+i] = 16,16
        upper[i],upper[count+i] = d.width-16-n.width,d.height-16-n.height
    if np.any(upper<lower):
        raise DiagramError("Infeasible canvas: a node and its text cannot fit at the requested size")
    rows,limits = [],[]
    def le(entries,limit):
        row = np.zeros(size)
        for k,v in entries:
            row[k] += v
        rows.append(row)
        limits.append(limit)
    for i,n in enumerate(diagram.nodes):
        for k,ref in [(i,n.x),(count+i,n.y)]:
            deviation = 2*count+k
            le([(k,1),(deviation,-1)],ref)
            le([(k,-1),(deviation,-1)],-ref)
    big = 2*max(d.width,d.height)+max(n.width+n.height for n in d.nodes)+gap
    for j,(a,b) in enumerate(pairs):
        k = 4*count+4*j
        le([(a,1),(b,-1),(k,big)],big-d.nodes[a].width-gap)
        le([(b,1),(a,-1),(k+1,big)],big-d.nodes[b].width-gap)
        le([(count+a,1),(count+b,-1),(k+2,big)],big-d.nodes[a].height-gap)
        le([(count+b,1),(count+a,-1),(k+3,big)],big-d.nodes[b].height-gap)
        le([(k+i,-1) for i in range(4)],-1)
    index = {n.id:i for i,n in enumerate(d.nodes)}
    if flow != "free":
        offset = count if flow=="vertical" else 0
        for e in d.edges:
            a,b = index[e.source],index[e.target]
            extent = d.nodes[a].height if offset else d.nodes[a].width
            le([(offset+a,1),(offset+b,-1)],-extent-gap)
    result = milp(objective,integrality=integer,bounds=Bounds(lower,upper),
                  constraints=LinearConstraint(np.array(rows),-np.inf,np.array(limits)),
                  options={"time_limit":time_limit,"mip_rel_gap":.01})
    if result.x is None:
        raise DiagramError(f"No feasible layout found: {result.message}")
    for i,n in enumerate(d.nodes):
        n.x,n.y = float(result.x[i]),float(result.x[count+i])
    nodes = {n.id:n for n in d.nodes}
    from .routing import OrthogonalRouter
    engine = OrthogonalRouter(nodes,d.width,d.height) if router=="visibility" else None
    routing = []
    for e in d.edges:
        if engine:
            e.points,evidence = engine.route(e.source,e.target)
            routing.append({"edge_id":e.id,**evidence})
        else:
            reroute(e,nodes,d.width,d.height)
    return d,{"method":"MILP minimum L1 node displacement with nonoverlap and fixed fitted node sizes",
              "solver_status":int(result.status),"optimal_within_tolerance":result.status==0,
              "objective":float(result.fun),"flow":flow,"gap":gap,"router":router,"routing":routing}
