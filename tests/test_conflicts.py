from copy import deepcopy
import json
from pathlib import Path
import random
import numpy as np
import pytest
from scipy.optimize import linprog
from constraint_recovery.model import Diagram,Node,Edge
from constraint_recovery.conflicts import diagnose,verify_certificate,LayoutConflict
from constraint_recovery.layout import edit
from constraint_recovery.cli import main


def chain(height=200):
    return Diagram(300,height,[Node("a",20,20,80,60),Node("b",120,20,80,60),Node("c",20,120,80,60)],
                   [Edge("ab","a","b"),Edge("bc","b","c")])


def test_longest_flow_path_provides_necessary_canvas_lower_bound():
    d=chain()
    c=diagnose(d,flow="vertical")
    assert c["kind"]=="flow_span" and c["node_ids"]==["a","b","c"]
    assert c["required"]==260 and c["available"]==200 and c["shortfall"]==60
    assert verify_certificate(d,c,flow="vertical")
    assert diagnose(chain(height=260),flow="vertical") is None


def test_directed_cycle_has_positive_increment_contradiction():
    d=chain(height=1000)
    d.edges.append(Edge("ca","c","a"))
    c=diagnose(d,flow="vertical")
    assert c["kind"]=="positive_flow_cycle" and c["cycle_increment"]==252
    assert c["contradiction"]=="0 >= 252"
    assert verify_certificate(d,c,flow="vertical")
    assert diagnose(d,flow="free") is None


def test_nested_dfs_cycle_witness_keeps_corresponding_edge_ids():
    d=chain(height=1000)
    d.nodes.append(Node("d",20,300,80,60))
    d.edges.extend([Edge("cd","c","d"),Edge("db","d","b")])
    c=diagnose(d,flow="horizontal")
    assert c["node_ids"]==["b","c","d","b"] and c["edge_ids"]==["bc","cd","db"]
    assert verify_certificate(d,c,flow="horizontal")


def test_node_and_area_bounds_are_independently_verified():
    d=Diagram(100,100,[Node("wide",0,0,80,30)],[])
    c=diagnose(d)
    assert c["kind"]=="node_canvas" and verify_certificate(d,c)
    d=Diagram(200,200,[Node(str(i),0,0,90,90) for i in range(4)],[])
    c=diagnose(d)
    assert c["kind"]=="area_bound" and verify_certificate(d,c)


@pytest.mark.parametrize("key,value",[("required",259),("available",201),("shortfall",59),("node_ids",["a","c"]),
                                     ("edge_ids",["bc","ab"]),("subject_sha256","wrong"),("kind","unknown"),("gap",0)])
def test_altered_witness_is_rejected(key,value):
    d=chain()
    c=diagnose(d,flow="vertical")
    c[key]=value
    assert not verify_certificate(d,c,flow="vertical")


def test_witness_is_bound_to_fitted_geometry_and_requested_flow():
    d=chain()
    c=diagnose(d,flow="vertical")
    d.nodes[0].height=59
    assert not verify_certificate(d,c,flow="vertical")
    assert not verify_certificate(chain(),c,flow="horizontal")


def test_layout_attaches_a_verified_certificate_after_text_fitting():
    d=chain()
    with pytest.raises(LayoutConflict) as error:
        edit(d,flow="vertical",font_size=24)
    exc=error.value
    assert verify_certificate(Diagram.from_dict(exc.fitted_diagram),exc.certificate,flow="vertical")
    assert d.nodes[0].font_size==16


def test_cli_saves_failure_witness_and_can_verify_it_without_solver(tmp_path,monkeypatch):
    source=Path(__file__).parents[1]/"examples/pipeline.svg"
    out=tmp_path/"impossible.svg"
    monkeypatch.setattr("sys.argv",["constraint-recovery","edit",str(source),"--output",str(out),"--flow","vertical","--height","200"])
    assert main()==2 and not out.exists()
    saved=out.with_suffix(".failure.json")
    record=json.loads(saved.read_text())
    assert record["status"]=="infeasible" and record["certificate"]["kind"]=="flow_span"
    def forbidden(*args,**kwargs):
        raise AssertionError("Witness verification must not call the solver")
    monkeypatch.setattr("constraint_recovery.layout.milp",forbidden)
    monkeypatch.setattr("sys.argv",["constraint-recovery","check-witness",str(saved)])
    assert main()==0
    record["certificate"]["required"]+=1
    saved.write_text(json.dumps(record))
    assert main()==2


def test_flow_witness_detection_matches_independent_linear_feasibility():
    rng=random.Random(21871)
    for _ in range(100):
        count=rng.randint(3,9)
        nodes=[Node(str(i),0,0,60,rng.randint(20,90)) for i in range(count)]
        edges=[Edge(f"{i}-{j}",str(i),str(j)) for i in range(count) for j in range(i+1,count) if rng.random()<.3]
        if rng.random()<.25:
            edges.append(Edge("back",str(count-1),"0"))
        d=Diagram(10000,rng.randint(150,600),nodes,edges)
        gap=rng.randint(0,36)
        rows,limits=[],[]
        for e in edges:
            row=np.zeros(count)
            u,v=int(e.source),int(e.target)
            row[u],row[v]=1,-1
            rows.append(row); limits.append(-nodes[u].height-gap)
        lp=linprog(np.zeros(count),A_ub=np.array(rows) if rows else None,b_ub=np.array(limits) if rows else None,
                   bounds=[(16,d.height-16-n.height) for n in nodes],method="highs")
        c=diagnose(d,flow="vertical",gap=gap)
        assert (c is not None)==(lp.status==2)
        if c:
            assert c["kind"] in {"positive_flow_cycle","flow_span"}
            assert verify_certificate(d,c,flow="vertical",gap=gap)


def test_no_witness_does_not_mean_full_packing_is_feasible():
    from constraint_recovery.model import DiagramError
    d=Diagram(200,200,[Node("a",0,0,100,100),Node("b",0,0,100,100)],[])
    assert diagnose(d) is None
    with pytest.raises(DiagramError,match="No feasible") as error:
        edit(d)
    assert not isinstance(error.value,LayoutConflict)
