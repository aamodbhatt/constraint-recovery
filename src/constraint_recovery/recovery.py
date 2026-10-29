"""Endpoint recovery, explicit review observations and source-bound overrides."""
from dataclasses import asdict
import hashlib
import math
from .model import Diagram,DiagramError,Edge
from .svg import endpoint,boundary_distance


def assemble(width,height,nodes,connectors,warnings,source_text,tolerance=8,attachment_model=None,
             attachment_overrides=None,review=False):
    identifiers=[n.id for n in nodes]+[key for key,_ in connectors]
    if any(not isinstance(key,str) or not key for key in identifiers) or len(set(identifiers))!=len(identifiers):
        raise DiagramError("Node and edge IDs must be nonempty and unique")
    overrides={} if attachment_overrides is None else attachment_overrides
    if not isinstance(overrides,dict) or set(overrides)-{key for key,_ in connectors}:
        raise DiagramError("Attachment override IDs do not match source connectors")
    known={n.id for n in nodes}
    for values in overrides.values():
        if not isinstance(values,dict) or not values or set(values)-{"source","target"} or any(not isinstance(v,str) or v not in known for v in values.values()):
            raise DiagramError("Attachment overrides need source/target IDs present in the SVG")
    edges,observations=[],[]
    for key,points in connectors:
        if len(points)<2 or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in points):
            raise DiagramError(f"Invalid connector geometry: {key}")
        choices={}
        observed={"id":key,"points":points}
        for role,index,neighbor in [("source",0,1),("target",-1,-2)]:
            p=points[index]
            toward=[p[k]-points[neighbor][k] for k in range(2)]
            selected=None
            reason=""
            if role in overrides.get(key,{}):
                selected=overrides[key][role]
                reason="Explicit source-bound attachment override; intent not independently verified"
            else:
                try:
                    selected=attachment_model.resolve(p,toward,nodes) if attachment_model else endpoint(p,nodes,tolerance)
                    reason="Experimental learned geometric choice" if attachment_model else "Unambiguous boundary proximity"
                except DiagramError as exc:
                    if not review:
                        raise
                    reason=str(exc)
            choices[role]=selected
            if review:
                candidates=[{"node_id":n.id,"boundary_distance":boundary_distance(p,n)} for n in nodes]
                if attachment_model:
                    try:
                        scores=attachment_model.scores(p,toward,nodes)
                        for candidate,score in zip(candidates,scores):
                            candidate["uncalibrated_model_score"]=float(score)
                    except DiagramError:
                        pass
                candidates.sort(key=lambda item:(item["boundary_distance"],item["node_id"]))
                observed[role]={"point":p,"toward":toward,"selected":selected,"reason":reason,"candidates":candidates}
        if review:
            observed["valid_pair"]=choices["source"] is not None and choices["target"] is not None and choices["source"]!=choices["target"]
            observations.append(observed)
        else:
            edge=Edge(key,choices["source"],choices["target"],points)
            if key in overrides:
                edge.evidence="Explicit user-supplied attachment override; not independent author-intent verification"
            elif attachment_model:
                edge.evidence="Experimental synthetic-trained endpoint ranker; review required; scores are not correctness guarantees"
            edges.append(edge)
    if review:
        return {"schema_version":1,"kind":"attachment-review","source_sha256":hashlib.sha256(source_text.encode()).hexdigest(),
                "width":width,"height":height,"nodes":[asdict(n) for n in nodes],"connectors":observations,
                "automatic_recovery_complete":all(r["valid_pair"] for r in observations),
                "unresolved_endpoints":sum(r[role]["selected"] is None for r in observations for role in ["source","target"]),
                "warnings":warnings+["Review observations are not an accepted constraint graph; model scores are not calibrated correctness probabilities"]}
    if overrides:
        warnings=warnings+["Explicit attachment overrides applied; inspect the requested relationships"]
    return Diagram(width,height,nodes,edges,warnings,source_sha256=hashlib.sha256(source_text.encode()).hexdigest()).validate()


def load_overrides(data,source_text):
    if not isinstance(data,dict) or data.get("schema_version")!=1 or data.get("kind")!="attachment-overrides":
        raise DiagramError("Unsupported attachment override schema")
    if data.get("source_sha256")!=hashlib.sha256(source_text.encode()).hexdigest():
        raise DiagramError("Attachment overrides belong to a different source SVG")
    if not isinstance(data.get("decisions"),dict):
        raise DiagramError("Attachment override decisions must be an object")
    return data["decisions"]
