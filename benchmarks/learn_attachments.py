"""CPU-only endpoint ranking experiment with predeclared held-out scene families."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time
import numpy as np
from scipy.special import softmax
from constraint_recovery.model import Node
from constraint_recovery.svg import boundary_distance
from constraint_recovery.attachment import FEATURES, AttachmentModel, features, fit


def scenes(seed,count,families):
    rng = random.Random(seed)
    for i in range(count):
        family = families[i%len(families)]
        scale = rng.uniform(.7,1.6)
        width,height = 100*scale,56*scale
        gap = rng.uniform(3,32)*scale
        nodes = []
        for j in range(6):
            x,y = (j*(width+gap),0) if family=="row" else (0,j*(height+gap))
            if family in {"grid","staggered"}:
                x,y = (j%3)*(width+gap),(j//3)*(height+gap)
            if family=="staggered":
                x += rng.uniform(-15,15)*scale
                y += rng.uniform(-12,12)*scale
            nodes.append(Node(f"node-{j}",40+x,40+y,width,height))
        truth = rng.choice(nodes)
        side = rng.randrange(4)
        fraction = rng.uniform(.15,.85)
        choices = [([truth.x,truth.y+fraction*height],[1,0]),
                   ([truth.x+width,truth.y+fraction*height],[-1,0]),
                   ([truth.x+fraction*width,truth.y],[0,1]),
                   ([truth.x+fraction*width,truth.y+height],[0,-1])]
        point,toward = choices[side]
        point = [v+rng.gauss(0,4.5*scale) for v in point]
        angle = math.atan2(toward[1],toward[0])+rng.uniform(-.25,.25)
        toward = [math.cos(angle),math.sin(angle)]
        rng.shuffle(nodes)
        target = next(k for k,n in enumerate(nodes) if n.id==truth.id)
        yield {"id":f"{seed}-{i}","family":family,"point":point,"toward":toward,"nodes":nodes,"target":target}


def groups(data):
    return [(features(s["point"],s["toward"],s["nodes"]),s["target"]) for s in data]


def metrics(data,weights,threshold):
    correct,nearest,directional,accepted,accepted_correct = 0,0,0,0,0
    probabilities,labels = [],[]
    per_family = {}
    for scene in data:
        x = features(scene["point"],scene["toward"],scene["nodes"])
        scores = softmax(x@weights)
        chosen = int(scores.argmax())
        hit = chosen==scene["target"]
        nearest += int(np.argmin(x[:,1])==scene["target"])
        # Stronger declared rule uses the visible connector tangent, not hidden truth.
        directional += int(np.argmin(x[:,1]+.25*(1-x[:,3]))==scene["target"])
        correct += int(hit)
        confidence = float(scores[chosen])
        allowed = confidence>=threshold and boundary_distance(scene["point"],scene["nodes"][chosen])<=24
        accepted += int(allowed)
        accepted_correct += int(allowed and hit)
        probabilities.append(confidence)
        labels.append(int(hit))
        bucket = per_family.setdefault(scene["family"],{"count":0,"correct":0})
        bucket["count"]+=1
        bucket["correct"]+=int(hit)
    ece = 0
    for bucket_index in range(10):
        mask = [i for i,p in enumerate(probabilities) if min(int(p*10),9)==bucket_index]
        if mask:
            ece += len(mask)/len(data)*abs(np.mean([probabilities[i] for i in mask])-np.mean([labels[i] for i in mask]))
    return {"count":len(data),"ranker_accuracy":correct/len(data),"nearest_boundary_accuracy":nearest/len(data),
            "directional_heuristic_accuracy":directional/len(data),"coverage":accepted/len(data),
            "accepted_error":1-accepted_correct/accepted if accepted else None,
            "top_label_ece_10_bins":float(ece),"families":per_family}


def choose_threshold(validation,weights):
    # A validation selection rule, not a distribution-free guarantee.
    for threshold in np.arange(.8,1,.01):
        result = metrics(validation,weights,float(threshold))
        if result["coverage"]*len(validation)>=50 and result["accepted_error"]<=.05:
            return float(threshold)
    return 1.000001


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/attachment-learning.json"))
    p.add_argument("--model",type=Path,default=Path("models/attachment-ranker.json"))
    p.add_argument("--train-scenes",type=int,default=1200)
    args = p.parse_args()
    if args.train_scenes<100:
        p.error("Use at least 100 training scenes")
    train = list(scenes(101,args.train_scenes,["row","column","grid"]))
    validation = list(scenes(202,300,["row","column","grid"]))
    test = list(scenes(303,600,["row","column","grid"]))
    shifted = list(scenes(404,600,["staggered"]))
    started = time.perf_counter()
    weights,optimization = fit(groups(train))
    seconds = time.perf_counter()-started
    threshold = choose_threshold(validation,weights)
    model = {"schema_version":1,"features":FEATURES,"weights":weights.tolist(),"threshold":threshold,
             "score_kind":"Uncalibrated candidate softmax; threshold selected on validation data",
             "training":"Synthetic endpoint scenes only; no author-intent supervision",
             "seeds":{"train":101,"validation":202,"test":303,"unseen_family":404}}
    report = {"task":"Choose the node intended by a noisy connector endpoint and visible tangent",
              "training_scenes":len(train),"training_candidates":sum(len(s["nodes"]) for s in train),
              "training_seconds":seconds,"device":"CPU","model":"Conditional logistic candidate ranker",
              "validation_threshold":threshold,"optimization":optimization,
              "validation":metrics(validation,weights,threshold),"test":metrics(test,weights,threshold),
              "unseen_family":metrics(shifted,weights,threshold),
              "limitations":["Synthetic geometric labels, not inferred author intent", "Separate seeds but same generator for in-family splits",
                             "Staggered family held out from training and threshold selection", "Validation risk target is empirical, not a guarantee",
                             "No claim of improvement over external data or modern AI editors"]}
    args.model.parent.mkdir(parents=True,exist_ok=True)
    args.model.write_text(json.dumps(model,indent=2)+"\n")
    report["model_sha256"] = hashlib.sha256(args.model.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
