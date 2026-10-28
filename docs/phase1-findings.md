# Phase 1 pilot findings

## Summary

This phase adds a real-source compatibility audit, a locally trained endpoint model, a mature layout baseline, explicit branch insertion and a data annotation protocol. It does not complete real-diagram relationship evaluation or establish a novel method.

## External ingestion is the immediate bottleneck

A predeclared prefix of 20 SciDiagramRevision test rows contains 19 SVGs and one missing source. M0 accepts none. First rejection reasons include transforms (3), filters (2), symbols (1), styles (5), images (3), curves (1), gradients (1), patterns (1), inherited group styles (2), and one absent SVG. Only the first failure per row is counted; fixing it does not imply the entire figure becomes supported.

Raw source figures were not committed. Identifiers, hashes and rejection reasons are in [the audit](../results/external-compatibility.json). This convenience sample is not a population estimate.

## First learned component: endpoint ownership

The CPU-trained conditional-logistic ranker sees geometry and connector tangents only. It uses 1,200 training scenes (7,200 node candidates), 300 validation scenes, 600 test scenes and 600 scenes from a held-out staggered family.

| Evaluation | Nearest boundary | Tangent-aware heuristic | Learned ranker |
|---|---:|---:|---:|
| In-family test | 97.50% | 100.00% | 100.00% |
| Held-out staggered family | 93.00% | 99.83% | 99.83% |

At the validation-selected score threshold of 0.8, the ranker accepts 71.83% of the in-family test and 58.50% of the held-out family, with no accepted errors observed. These coverage figures concern the ranker only; selective performance of competing heuristics has not been compared. Candidate softmax scores are not calibrated probabilities or formal guarantees. The reported top-label calibration errors are approximately 0.159 and 0.196 respectively.

The model ties the stronger heuristic. It would be incorrect to claim that AI has improved relationship recovery over competent hand-written geometry. The model and result are retained as a baseline. All data here is synthetic; none demonstrates recovery of author-intended alignment or grouping from a real figure.

## ELK comparison isolates layout

ELK 0.12.1 and the MILP engine receive the same supplied graph and fitted text on 15 generated chain, branch and diamond scenarios. Both outputs are checked against a fixed canvas without scaling text. The MILP pipeline passes 10 cases and declares the five tight-canvas cases infeasible; ELK passes 7 fixed-canvas checks. Full natural ELK extents and case errors are retained in [the comparison](../results/elk-comparison.json).

This is a comparison of two declared configurations with different objectives. MILP minimizes displacement under fixed canvas constraints, while the ELK configuration computes layered layouts. It is not a general claim that MILP is superior to ELK, and there is no learned inference advantage in this experiment. Node-process startup is included in ELK timings, so they are not used for an algorithm-speed claim. Direct LLM editing has not been benchmarked.

Reproduce the optional baseline:

```sh
npm ci --ignore-scripts
PYTHONPATH=src python benchmarks/compare_elk.py
```

## Next work and cloud decision

Priority is broader, non-destructive SVG ingestion and independently reviewed relationships from real diagrams. Keep unsupported figures in the ingestion denominator. Then assess repeated-edit preservation and add stronger inference baselines and uncertainty evaluation.

The local ranker trains in less than a second in this pilot. There is no measured GPU bottleneck and no justification to spend cloud credits yet. No cloud resources were started.
