"""Orthogonal visibility-grid routing with explicit clearance and bend costs."""
import heapq
import math
import numpy as np
from .model import DiagramError
from .check import segment_hits_rect


def simplify(points):
    result = []
    for p in points:
        if result and math.dist(result[-1],p)<1e-8:
            continue
        while len(result)>1 and ((abs(result[-2][0]-result[-1][0])<1e-8 and abs(p[0]-result[-1][0])<1e-8) or
                                  (abs(result[-2][1]-result[-1][1])<1e-8 and abs(p[1]-result[-1][1])<1e-8)):
            result.pop()
        result.append(list(p))
    return result


class OrthogonalRouter:
    def __init__(self,nodes,width,height,clearance=8,bend_penalty=8,max_states=65536):
        self.nodes = nodes
        self.width,self.height = width,height
        self.clearance,self.bend_penalty = clearance,bend_penalty
        self.max_states = max_states
        if not all(math.isfinite(v) for v in [width,height,clearance,bend_penalty]) or min(width,height)<=0 or min(clearance,bend_penalty)<0:
            raise DiagramError("Routing dimensions/costs must be finite with nonnegative clearance and bend penalty")
        self.boxes = {key:(n.x-clearance,n.y-clearance,n.x+n.width+clearance,n.y+n.height+clearance) for key,n in nodes.items()}
        # Shared Hanan coordinates: inflated obstacle sides and center-port axes.
        xs,ys = {0.,float(width)},{0.,float(height)}
        for key,n in nodes.items():
            x0,y0,x1,y1 = self.boxes[key]
            xs.update(x for x in [x0,x1,n.x+n.width/2] if 0<=x<=width)
            ys.update(y for y in [y0,y1,n.y+n.height/2] if 0<=y<=height)
        self.x,self.y = np.asarray(sorted(xs)),np.asarray(sorted(ys))
        if len(self.x)*len(self.y)>100000:
            raise DiagramError("Orthogonal routing grid exceeds its vertex budget")
        self.x_index = {float(x):i for i,x in enumerate(self.x)}
        self.y_index = {float(y):i for i,y in enumerate(self.y)}
        self.valid = np.ones((len(self.y),len(self.x)),dtype=bool)
        self.horizontal = np.ones((len(self.y),len(self.x)-1),dtype=bool)
        self.vertical = np.ones((len(self.y)-1,len(self.x)),dtype=bool)
        for x0,y0,x1,y1 in self.boxes.values():
            inside_x = (self.x>x0+1e-8)&(self.x<x1-1e-8)
            inside_y = (self.y>y0+1e-8)&(self.y<y1-1e-8)
            self.valid &= ~(inside_y[:,None]&inside_x[None,:])
            cross_x = (self.x[:-1]<x1-1e-8)&(self.x[1:]>x0+1e-8)
            cross_y = (self.y[:-1]<y1-1e-8)&(self.y[1:]>y0+1e-8)
            self.horizontal &= ~(inside_y[:,None]&cross_x[None,:])
            self.vertical &= ~(cross_y[:,None]&inside_x[None,:])

    def portals(self,key):
        n,c = self.nodes[key],self.clearance
        cx,cy = n.x+n.width/2,n.y+n.height/2
        options = [([n.x,cy],[n.x-c,cy],0),([n.x+n.width,cy],[n.x+n.width+c,cy],0),
                   ([cx,n.y],[cx,n.y-c],1),([cx,n.y+n.height],[cx,n.y+n.height+c],1)]
        accepted = []
        for port,stub,axis in options:
            if stub[0] not in self.x_index or stub[1] not in self.y_index:
                continue
            iy,ix = self.y_index[stub[1]],self.x_index[stub[0]]
            if not self.valid[iy,ix]:
                continue
            # Escape the endpoint's own inflated box, never another obstacle.
            collision = False
            for other,box in self.boxes.items():
                if other==key:
                    continue
                x0,y0,x1,y1 = box
                if axis==0:
                    collision |= y0+1e-8<port[1]<y1-1e-8 and max(min(port[0],stub[0]),x0)<min(max(port[0],stub[0]),x1)-1e-8
                else:
                    collision |= x0+1e-8<port[0]<x1-1e-8 and max(min(port[1],stub[1]),y0)<min(max(port[1],stub[1]),y1)-1e-8
            if not collision:
                accepted.append((iy,ix,axis,port,stub))
        return accepted

    def route(self,source,target):
        if source not in self.nodes or target not in self.nodes or source==target:
            raise DiagramError("Invalid routing endpoint IDs")
        starts,ends = self.portals(source),self.portals(target)
        if not starts or not ends:
            raise DiagramError("No available center port at the requested routing clearance")
        distance,previous,origin = {},{},{}
        heap = []
        for i,(iy,ix,axis,port,stub) in enumerate(starts):
            state = (iy,ix,axis)
            distance[state] = math.dist(port,stub)
            previous[state] = None
            origin[state] = i
            heapq.heappush(heap,(distance[state],state))
        targets = {}
        for i,(iy,ix,axis,port,stub) in enumerate(ends):
            targets.setdefault((iy,ix),[]).append(i)
        best = math.inf
        terminal = None
        visited = 0
        while heap:
            cost,state = heapq.heappop(heap)
            if cost!=distance[state]:
                continue
            if cost>best:
                break
            visited+=1
            if visited>self.max_states:
                raise DiagramError("Orthogonal routing search exceeded its state budget")
            iy,ix,axis = state
            for end_index in targets.get((iy,ix),[]):
                end = ends[end_index]
                candidate = cost+math.dist(end[3],end[4])+(self.bend_penalty if axis!=end[2] else 0)
                if candidate<best:
                    best,terminal = candidate,(state,end_index)
            neighbors = []
            if ix and self.horizontal[iy,ix-1]:
                neighbors.append((iy,ix-1,0))
            if ix+1<len(self.x) and self.horizontal[iy,ix]:
                neighbors.append((iy,ix+1,0))
            if iy and self.vertical[iy-1,ix]:
                neighbors.append((iy-1,ix,1))
            if iy+1<len(self.y) and self.vertical[iy,ix]:
                neighbors.append((iy+1,ix,1))
            for nxt in neighbors:
                ny,nx,new_axis = nxt
                if not self.valid[ny,nx]:
                    continue
                step = abs(self.x[nx]-self.x[ix])+abs(self.y[ny]-self.y[iy])
                new_cost = cost+step+(self.bend_penalty if axis!=new_axis else 0)
                if new_cost<distance.get(nxt,math.inf):
                    distance[nxt],previous[nxt],origin[nxt] = new_cost,state,origin[state]
                    heapq.heappush(heap,(new_cost,nxt))
        if terminal is None:
            raise DiagramError("No orthogonal route on the center-port visibility grid at the requested clearance")
        state,end_index = terminal
        start = starts[origin[state]]
        path = [ends[end_index][3]]
        while state is not None:
            iy,ix,_ = state
            path.append([float(self.x[ix]),float(self.y[iy])])
            state = previous[state]
        path.append(start[3])
        path = simplify(list(reversed(path)))
        # Separate geometric guard, using original boxes rather than grid masks.
        if any(segment_hits_rect(p,q,n) for p,q in zip(path,path[1:]) for n in self.nodes.values()):
            raise DiagramError("Routing guard detected a node-interior crossing")
        return path,{"method":"orthogonal visibility grid with Dijkstra over position and incoming axis",
                     "clearance":self.clearance,"bend_penalty":self.bend_penalty,
                     "search_cost":float(best),"length":sum(math.dist(p,q) for p,q in zip(path,path[1:])),
                     "bends":max(0,len(path)-2),"visited_states":visited,
                     "grid_vertices":int(self.valid.sum())}
