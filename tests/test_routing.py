from copy import deepcopy
from dataclasses import replace
import math
import pytest
from constraint_recovery.model import Node,Edge,Diagram,DiagramError
from constraint_recovery.routing import OrthogonalRouter
from constraint_recovery.layout import reroute
from constraint_recovery.check import verify,segment_hits_rect


def maze():
    nodes=[Node("a",20,100,40,40),Node("b",520,100,40,40)]
    for i,x in enumerate([130,240,350,450]):
        nodes.append(Node(f"barrier-{i}",x,0 if i%2==0 else 100,30,200))
    return Diagram(600,300,nodes,[Edge("ab","a","b")]).validate()


def test_visibility_route_solves_alternating_barriers_where_templates_fail():
    d=maze()
    nodes={n.id:n for n in d.nodes}
    with pytest.raises(DiagramError,match="No collision-free"):
        reroute(deepcopy(d.edges[0]),nodes,d.width,d.height,clearance=8)
    path,evidence=OrthogonalRouter(nodes,d.width,d.height).route("a","b")
    d.edges[0].points=path
    assert verify(d,d)["passed"]
    assert evidence["bends"]>=6
    assert evidence["search_cost"]==pytest.approx(evidence["length"]+8*evidence["bends"])
    for n in d.nodes[2:]:
        padded=replace(n,x=n.x-8,y=n.y-8,width=n.width+16,height=n.height+16)
        assert not any(segment_hits_rect(p,q,padded) for p,q in zip(path,path[1:]))


def test_straight_route_has_known_optimal_cost():
    nodes={n.id:n for n in [Node("a",20,40,80,60),Node("b",220,40,80,60)]}
    path,evidence=OrthogonalRouter(nodes,400,200).route("a","b")
    assert path==[[100,70],[220,70]]
    assert evidence["length"]==120 and evidence["bends"]==0 and evidence["search_cost"]==120


def test_router_deterministic_and_input_immutable():
    d=maze()
    before=d.to_dict()
    router=OrthogonalRouter({n.id:n for n in d.nodes},d.width,d.height)
    assert router.route("a","b")==router.route("a","b")
    assert d.to_dict()==before


def test_full_height_barrier_fails_with_clearance():
    d=maze()
    d.nodes=[d.nodes[0],d.nodes[1],Node("wall",200,0,30,300)]
    router=OrthogonalRouter({n.id:n for n in d.nodes},d.width,d.height)
    with pytest.raises(DiagramError,match="No orthogonal route"):
        router.route("a","b")


def test_search_budget_failure_is_explicit():
    d=maze()
    router=OrthogonalRouter({n.id:n for n in d.nodes},d.width,d.height,max_states=1)
    with pytest.raises(DiagramError,match="state budget"):
        router.route("a","b")


@pytest.mark.parametrize("options",[{"clearance":-1},{"clearance":math.nan},{"bend_penalty":-1}])
def test_invalid_routing_parameters(options):
    with pytest.raises(DiagramError):
        OrthogonalRouter({},400,200,**options)
