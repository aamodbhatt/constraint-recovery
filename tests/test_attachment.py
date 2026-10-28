import json
from pathlib import Path
import numpy as np
import pytest
from constraint_recovery.attachment import FEATURES,AttachmentModel,features,fit
from constraint_recovery.model import Node,DiagramError
from constraint_recovery.svg import parse_svg

ROOT = Path(__file__).parents[1]


def test_supervision_changes_learned_ranking():
    x = np.zeros((2,len(FEATURES)))
    x[0,1],x[1,1] = 0,2
    a,_ = fit([(x,0)]*8)
    b,_ = fit([(x,1)]*8)
    assert (x@a).argmax()==0
    assert (x@b).argmax()==1


def test_predictions_do_not_depend_on_candidate_ids_or_order():
    nodes = [Node("a",0,0,100,60),Node("b",300,0,100,60)]
    model = AttachmentModel([0,-8,-1,2,0,0,0,0,0])
    before = model.scores([100,30],[-1,0],nodes)
    nodes[0].id,nodes[1].id = "unseen-name","another"
    after = model.scores([100,30],[-1,0],list(reversed(nodes)))
    assert np.allclose(before,after[::-1])


def test_identical_observations_require_abstention():
    nodes = [Node("possible-author-intent-a",0,0,100,60),Node("possible-author-intent-b",0,0,100,60)]
    model = AttachmentModel([0,-8,-1,2,0,0,0,0,0],threshold=.8)
    assert np.allclose(model.scores([100,30],[-1,0],nodes),[.5,.5])
    with pytest.raises(DiagramError,match="abstained"):
        model.resolve([100,30],[-1,0],nodes)


def test_far_away_input_cannot_auto_execute_even_at_high_score():
    model = AttachmentModel([0,-8,-1,2,0,0,0,0,0])
    with pytest.raises(DiagramError,match="abstained"):
        model.resolve([500,500],[1,0],[Node("a",0,0,100,60)])


def test_invalid_model_schema_rejected(tmp_path):
    p = tmp_path/"bad.json"
    p.write_text(json.dumps({"schema_version":1,"features":["wrong"],"weights":[0]}))
    with pytest.raises(DiagramError):
        AttachmentModel.load(p)


def test_experimental_model_is_opt_in_and_marks_its_evidence():
    source = (ROOT/"examples/pipeline.svg").read_text()
    geometric = parse_svg(source)
    model = AttachmentModel.load(ROOT/"models/attachment-ranker.json")
    learned = parse_svg(source,attachment_model=model)
    assert [(e.source,e.target) for e in learned.edges]==[(e.source,e.target) for e in geometric.edges]
    assert all("Experimental" in e.evidence for e in learned.edges)
    assert len(model.decisions)==4


@pytest.mark.parametrize("bad",[float("nan"),float("inf"),-1])
def test_invalid_threshold_is_rejected(bad):
    with pytest.raises(DiagramError):
        AttachmentModel(np.zeros(len(FEATURES)),threshold=bad)


@pytest.mark.parametrize("point,direction",[([float("nan"),0],[1,0]),([0,0],[0,0]),([1],[1,0])])
def test_malformed_observations_cannot_produce_actions(point,direction):
    model = AttachmentModel(np.zeros(len(FEATURES)))
    with pytest.raises(DiagramError,match="abstained"):
        model.resolve(point,direction,[Node("a",0,0,100,60)])


def test_invalid_svg_geometry_is_rejected_before_learned_scoring():
    source = (ROOT/"examples/pipeline.svg").read_text().replace('width="170"','width="0"',1)
    model = AttachmentModel.load(ROOT/"models/attachment-ranker.json")
    with pytest.raises(DiagramError,match="Non-positive"):
        parse_svg(source,attachment_model=model)
    assert model.decisions==[]
