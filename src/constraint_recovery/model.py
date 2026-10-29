from dataclasses import asdict, dataclass, field
import math
import re


class DiagramError(ValueError):
    pass


@dataclass
class Node:
    id: str
    x: float
    y: float
    width: float
    height: float
    label: str = ""
    font_size: float = 16
    fill: str = "#eef3fb"
    stroke: str = "#30445f"
    lines: list[str] = field(default_factory=list)


@dataclass
class Edge:
    id: str
    source: str
    target: str
    points: list[list[float]] = field(default_factory=list)
    evidence: str = "unambiguous boundary proximity; not author-confirmed semantics"


@dataclass
class Diagram:
    width: float
    height: float
    nodes: list[Node]
    edges: list[Edge]
    warnings: list[str] = field(default_factory=list)
    schema_version: int = 1
    source_sha256: str | None = None

    def validate(self):
        if self.source_sha256 is not None and (not isinstance(self.source_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",self.source_sha256)):
            raise DiagramError("Invalid source SHA-256 digest")
        if not all(math.isfinite(v) and v > 0 for v in [self.width, self.height]):
            raise DiagramError("Canvas dimensions must be finite and positive")
        ids = [n.id for n in self.nodes] + [e.id for e in self.edges]
        if any(not isinstance(identifier,str) or not identifier for identifier in ids):
            raise DiagramError("Node and edge IDs must be nonempty strings")
        if len(ids) != len(set(ids)):
            raise DiagramError("Node and edge IDs must be unique")
        known = {n.id for n in self.nodes}
        for n in self.nodes:
            if not isinstance(n.label,str) or not isinstance(n.lines,list) or any(not isinstance(line,str) for line in n.lines):
                raise DiagramError(f"Invalid label or text lines: {n.id}")
            if not all(math.isfinite(v) for v in [n.x, n.y, n.width, n.height, n.font_size]):
                raise DiagramError(f"Non-finite geometry: {n.id}")
            if min(n.width, n.height, n.font_size) <= 0:
                raise DiagramError(f"Non-positive size: {n.id}")
        for e in self.edges:
            if e.source not in known or e.target not in known or e.source == e.target:
                raise DiagramError(f"Invalid edge endpoints: {e.id}")
            if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in e.points):
                raise DiagramError(f"Invalid connector geometry: {e.id}")
        return self

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data,dict):
            raise DiagramError("Constraint graph must be an object")
        if data.get("schema_version", 1) != 1:
            raise DiagramError("Unsupported constraint graph schema")
        return cls(data["width"], data["height"],
                   [Node(**n) for n in data["nodes"]],
                   [Edge(**e) for e in data["edges"]], data.get("warnings", []),
                   source_sha256=data.get("source_sha256")).validate()
