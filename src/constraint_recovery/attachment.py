"""Experimental conditional-logistic endpoint ranker. Geometry only; no semantic claims."""
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from .svg import boundary_distance
from .model import DiagramError

FEATURES = ["bias", "boundary_distance", "center_distance", "direction_alignment",
            "inside", "x_face_distance", "y_face_distance", "direction_x", "direction_y"]


def features(point, toward, nodes):
    p = np.asarray(point,dtype=float)
    t = np.asarray(toward,dtype=float)
    if p.shape!=(2,) or t.shape!=(2,) or not np.isfinite(p).all() or not np.isfinite(t).all() or np.linalg.norm(t)<1e-9:
        raise DiagramError("Invalid or directionless endpoint observation; abstained")
    if not nodes:
        raise DiagramError("No endpoint candidates; abstained")
    t = t/max(np.linalg.norm(t),1e-9)
    result = []
    for n in nodes:
        scale = math.sqrt(n.width*n.height)
        delta = np.array([n.x+n.width/2,n.y+n.height/2])-p
        distance = np.linalg.norm(delta)
        alignment = np.dot(delta,t)/max(distance,1e-9)
        fx = min(abs(p[0]-n.x),abs(p[0]-n.x-n.width))/scale
        fy = min(abs(p[1]-n.y),abs(p[1]-n.y-n.height))/scale
        inside = n.x<p[0]<n.x+n.width and n.y<p[1]<n.y+n.height
        result.append([1,boundary_distance(p,n)/scale,distance/scale,alignment,float(inside),fx,fy,
                       abs(t[0]),abs(t[1])])
    matrix = np.asarray(result)
    if not np.isfinite(matrix).all():
        raise DiagramError("Non-finite endpoint features; abstained")
    return matrix


def fit(groups, regularization=.1):
    if not groups or regularization<=0:
        raise ValueError("Nonempty training groups and positive regularization required")
    for x,target in groups:
        if x.ndim!=2 or x.shape[1]!=len(FEATURES) or not np.isfinite(x).all() or not 0<=target<len(x):
            raise ValueError("Invalid training group")
    def loss(w):
        value = regularization*np.dot(w,w)/2
        grad = regularization*w.copy()
        for x,target in groups:
            logits = x@w
            value += (logsumexp(logits)-logits[target])/len(groups)
            grad += (softmax(logits)@x-x[target])/len(groups)
        return value,grad
    result = minimize(loss,np.zeros(len(FEATURES)),jac=True,method="L-BFGS-B",options={"maxiter":200})
    if not result.success:
        raise RuntimeError(f"Ranker training failed: {result.message}")
    return result.x,{"objective":float(result.fun),"iterations":int(result.nit)}


class AttachmentModel:
    def __init__(self, weights, threshold=.9):
        self.weights = np.asarray(weights,dtype=float)
        if self.weights.shape!=(len(FEATURES),) or not np.isfinite(self.weights).all():
            raise DiagramError("Invalid endpoint model weights")
        if not math.isfinite(threshold) or not .5 <= threshold <= 1.000001:
            raise DiagramError("Invalid endpoint confidence threshold")
        self.threshold = float(threshold)
        self.decisions = []

    @classmethod
    def load(cls,path):
        data = json.loads(Path(path).read_text())
        if data.get("schema_version")!=1 or data.get("features")!=FEATURES:
            raise DiagramError("Unsupported endpoint model schema")
        return cls(data["weights"],data["threshold"])

    def scores(self,point,toward,nodes):
        return softmax(features(point,toward,nodes)@self.weights)

    def resolve(self,point,toward,nodes):
        scores = self.scores(point,toward,nodes)
        index = int(np.argmax(scores))
        probability = float(scores[index])
        if probability<self.threshold or boundary_distance(point,nodes[index])>24:
            raise DiagramError(f"Learned endpoint model abstained at {point}; confidence={probability:.3f}")
        self.decisions.append({"node":nodes[index].id,"score":probability})
        return nodes[index].id
