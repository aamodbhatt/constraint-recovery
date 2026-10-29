"""Bounded geometry normalization for an explicitly supported SVG subset."""
import math
import re
import numpy as np
from .model import DiagramError

NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"


def numbers(value):
    if re.sub(NUMBER,"",value).strip(" ,\t\n\r"):
        raise DiagramError(f"Invalid numeric list: {value[:80]}")
    result = [float(v) for v in re.findall(NUMBER,value)]
    if not all(math.isfinite(v) for v in result):
        raise DiagramError("Non-finite SVG geometry")
    return result


def transform(value):
    matrix = np.eye(3)
    consumed = 0
    for match in re.finditer(r"([A-Za-z]+)\s*\(([^)]*)\)",value):
        if value[consumed:match.start()].strip(" ,\n\t"):
            raise DiagramError("Invalid transform list")
        name,raw = match.groups()
        v = numbers(raw)
        step = np.eye(3)
        if name=="translate" and len(v) in {1,2}:
            step[:2,2] = [v[0],v[1] if len(v)==2 else 0]
        elif name=="scale" and len(v) in {1,2}:
            sx,sy = v[0],v[1] if len(v)==2 else v[0]
            step[0,0],step[1,1] = sx,sy
        elif name=="matrix" and len(v)==6:
            a,b,c,d,e,f = v
            step = np.array([[a,c,e],[b,d,f],[0,0,1]],dtype=float)
        elif name=="rotate" and len(v) in {1,3} and abs(v[0]%360)<1e-9:
            pass
        else:
            raise DiagramError(f"Unsupported transform: {name}; only translation and positive uniform scale are editable")
        matrix = matrix@step
        consumed = match.end()
    if value[consumed:].strip():
        raise DiagramError("Invalid transform syntax")
    scale(matrix)
    return matrix


def scale(matrix):
    if (not np.isfinite(matrix).all() or matrix[0,0]<=0 or
        not np.allclose(matrix[:2,:2],np.eye(2)*matrix[0,0],rtol=1e-9,atol=1e-10)):
        raise DiagramError("Rotation, reflection, skew and nonuniform scale require a shape-aware importer")
    return float(matrix[0,0])


def point(matrix,x,y):
    value = matrix@np.array([x,y,1.])
    if not np.isfinite(value).all():
        raise DiagramError("Non-finite transformed point")
    return value[:2].tolist()


def curve_points(path_data,matrix,tolerance=.2,max_points=4096):
    if not math.isfinite(tolerance) or tolerance<=0 or max_points<2:
        raise DiagramError("Curve subdivision needs a positive finite tolerance and at least two points")
    from svgpathtools import parse_path,Line,QuadraticBezier,CubicBezier
    try:
        path = parse_path(path_data)
    except Exception as exc:
        raise DiagramError(f"Invalid connector path: {exc}") from exc
    if not path or not path.iscontinuous() or path.isclosed():
        raise DiagramError("Expected an open connector path")
    output = []
    def convert(z):
        return np.asarray(point(matrix,z.real,z.imag))
    def flatten(segment,depth=0):
        if len(output)>=max_points or depth>20:
            raise DiagramError("Curve exceeds bounded subdivision budget")
        if not isinstance(segment,(Line,QuadraticBezier,CubicBezier)):
            raise DiagramError("Arc connectors are not supported yet")
        controls = [convert(z) for z in segment.bpoints()]
        a,b = controls[0],controls[-1]
        chord = b-a
        length2 = float(chord@chord)
        distances = []
        for p in controls[1:-1]:
            s = np.clip(float((p-a)@chord)/length2,0,1) if length2 else 0
            distances.append(float(np.linalg.norm(p-(a+s*chord))))
        if not distances or max(distances)<=tolerance:
            output.append(b.tolist())
            return
        left,right = segment.split(.5)
        flatten(left,depth+1)
        flatten(right,depth+1)
    previous = None
    for segment in path:
        if previous is not None and abs(segment.start-previous)>1e-8:
            raise DiagramError("Disconnected connector subpaths are unsupported")
        if not output:
            output.append(convert(segment.start).tolist())
        flatten(segment)
        previous = segment.end
    return output
